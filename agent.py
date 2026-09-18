import json, sqlite3, threading, time, webbrowser
from datetime import datetime
from pathlib import Path
import psutil
from flask import Flask, jsonify, request, render_template
from browser_history import BrowserHistoryReader
from policy import PolicyEngine

BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "config.json"
DB_PATH = BASE / "data" / "guardian.db"

AI_SERVICES = {
    "chatgpt": "ChatGPT", "openai": "OpenAI", "gemini": "Gemini",
    "claude": "Claude", "copilot": "Microsoft Copilot",
    "perplexity": "Perplexity", "poe": "Poe", "character.ai": "Character.AI",
    "ollama": "Ollama", "lm studio": "LM Studio"
}
BROWSERS = ["chrome", "msedge", "firefox"]

app = Flask(__name__, template_folder="templates", static_folder="static")

def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

def save_config(cfg):
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_PATH)

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, app TEXT,
        detail TEXT, duration_seconds INTEGER DEFAULT 0, risk TEXT DEFAULT 'INFO')""")
    con.execute("""CREATE TABLE IF NOT EXISTS sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, service TEXT, started TEXT,
        ended TEXT, duration_seconds INTEGER DEFAULT 0)""")
    con.commit(); con.close()

def add_event(kind, app_name="", detail="", risk="INFO", duration=0):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO events(ts,kind,app,detail,duration_seconds,risk) VALUES(?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), kind, app_name, detail, duration, risk))
    con.commit(); con.close()

def events(limit=100):
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close(); return [dict(x) for x in rows]

def sessions():
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 100").fetchall()
    con.close(); return [dict(x) for x in rows]

def upsert_session(service, started, ended, duration):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO sessions(service,started,ended,duration_seconds) VALUES(?,?,?,?)",
                (service, datetime.fromtimestamp(started).isoformat(timespec="seconds"),
                 datetime.fromtimestamp(ended).isoformat(timespec="seconds"), duration))
    con.commit(); con.close()

def detect_ai_processes():
    result = []
    for p in psutil.process_iter(["pid","name"]):
        try:
            name = (p.info["name"] or "").lower()
            for key, service in AI_SERVICES.items():
                if key in name:
                    result.append({"pid": p.info["pid"], "service": service,
                                   "process": p.info["name"], "model": "Not exposed"})
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return result

def battery():
    b = psutil.sensors_battery()
    if not b: return {"available": False}
    return {"available": True, "percent": round(b.percent,1),
            "plugged": bool(b.power_plugged),
            "state": "CHARGING" if b.power_plugged else "ON BATTERY"}

class GuardianAgent:
    def __init__(self):
        init_db()
        self.cfg = load_config()
        self.policy = PolicyEngine(self.cfg)
        self.history = BrowserHistoryReader()
        self.stop = threading.Event()
        self.last_system = 0
        self.last_browser = 0
        self.last_ai = set()
        self.ai_started = {}
        self.latest = {"ai":[],"processes":[],"websites":[],"battery":{},"updated":None}

    def collect(self):
        now = time.time()
        if now - self.last_system >= self.cfg["monitoring"]["system_poll_seconds"]:
            self.last_system = now
            ai = detect_ai_processes()
            current = {f'{x["pid"]}:{x["service"]}' for x in ai}
            for key in current - self.last_ai:
                service = key.split(":",1)[1]
                self.ai_started[key] = now
                add_event("AI_SESSION_STARTED", service, "AI-related local process observed")
            for key in self.last_ai - current:
                start = self.ai_started.pop(key, now)
                service = key.split(":",1)[1]
                dur = max(0, int(now-start))
                upsert_session(service, start, now, dur)
                add_event("AI_SESSION_ENDED", service, "AI-related local process ended", "INFO", dur)
            self.last_ai = current
            self.latest["ai"] = ai
            self.latest["processes"] = [{"pid":p.pid,"name":p.info.get("name","")}
                                        for p in psutil.process_iter(["name"])
                                        if p.info.get("name")][:100]
        if now - self.last_browser >= self.cfg["monitoring"]["browser_history_poll_seconds"]:
            self.last_browser = now
            self.latest["websites"] = self.history.read_recent(30)
        self.latest["battery"] = battery()
        self.latest["updated"] = datetime.now().isoformat(timespec="seconds")

    def run(self):
        while not self.stop.is_set():
            try: self.collect()
            except Exception as e: add_event("AGENT_ERROR","EDGEGUARD",str(e),"WARNING")
            self.stop.wait(1)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        url=f'http://{self.cfg["server"]["host"]}:{self.cfg["server"]["port"]}'
        print("EDGEGUARD:", url)
        try: webbrowser.open(url)
        except Exception: pass
        app.run(host=self.cfg["server"]["host"], port=self.cfg["server"]["port"],
                debug=False, threaded=True)

AGENT=GuardianAgent()

@app.get("/")
def index(): return render_template("dashboard.html")

@app.get("/api/status")
def status(): return jsonify({"latest":AGENT.latest,"events":events(80),"sessions":sessions()})

@app.get("/api/config")
def get_config(): return jsonify(AGENT.cfg)

@app.post("/api/config")
def set_config():
    AGENT.cfg=request.get_json(force=True)
    save_config(AGENT.cfg); AGENT.policy=PolicyEngine(AGENT.cfg)
    add_event("SETTINGS_CHANGED","EDGEGUARD","Local configuration updated")
    return jsonify({"ok":True})

@app.post("/api/rule")
def add_rule():
    p=request.get_json(force=True); cfg=AGENT.cfg
    cfg.setdefault("rules",[]).append({"type":p.get("type","app"),
        "target":p.get("target",""),"action":p.get("action","ASK")})
    save_config(cfg); AGENT.cfg=cfg
    add_event("POLICY_CHANGED","EDGEGUARD",f'{p.get("target","")} -> {p.get("action","ASK")}')
    return jsonify({"ok":True})

@app.post("/api/schedule")
def add_schedule():
    p=request.get_json(force=True); cfg=AGENT.cfg
    cfg.setdefault("schedules",[]).append({
        "name":p.get("name","Schedule"),"start":p.get("start","18:00"),
        "end":p.get("end","20:00"),"days":p.get("days",["Mon","Tue","Wed","Thu","Fri"]),
        "action":p.get("action","ALERT")})
    save_config(cfg); AGENT.cfg=cfg
    add_event("SCHEDULE_CHANGED","EDGEGUARD",p.get("name","Schedule"))
    return jsonify({"ok":True})

@app.post("/api/clear-events")
def clear_events():
    con=sqlite3.connect(DB_PATH); con.execute("DELETE FROM events"); con.commit(); con.close()
    return jsonify({"ok":True})

if __name__=="__main__":
    AGENT.start()
