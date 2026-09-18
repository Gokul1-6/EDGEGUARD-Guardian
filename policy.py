from datetime import datetime
from pathlib import Path

class PolicyEngine:
    ACTIONS={"ALLOW","ASK","BLOCK"}
    def __init__(self,cfg): self.cfg=cfg
    def decide(self,target,kind="app"):
        for r in self.cfg.get("rules",[]):
            if r.get("type")==kind and r.get("target","").lower() in target.lower():
                a=r.get("action","ASK").upper()
                if a in self.ACTIONS:return a
        return self.cfg.get("policies",{}).get(
            {"ai":"ai_service_default","private":"private_folder_default"}.get(kind,"ai_service_default"),"ASK")
    def in_schedule(self):
        now=datetime.now(); day=now.strftime("%a"); current=now.strftime("%H:%M")
        for s in self.cfg.get("schedules",[]):
            if day not in s.get("days",[]): continue
            a,b=s.get("start","18:00"),s.get("end","20:00")
            active=(a<=current<=b) if a<=b else (current>=a or current<=b)
            if active:return s
        return None
