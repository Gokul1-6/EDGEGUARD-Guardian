import shutil, sqlite3, tempfile, time
from pathlib import Path
from urllib.parse import urlparse

class BrowserHistoryReader:
    def __init__(self): self.home=Path.home()

    def copydb(self, src):
        if not src.exists(): return None
        try:
            dst=Path(tempfile.gettempdir())/f"edgeguard_{src.name}_{int(time.time()*1000)}"
            shutil.copy2(src,dst); return dst
        except Exception: return None

    def sources(self):
        chrome=self.home/"AppData/Local/Google/Chrome/User Data"
        edge=self.home/"AppData/Local/Microsoft/Edge/User Data"
        firefox=self.home/"AppData/Roaming/Mozilla/Firefox/Profiles"
        out=[]
        for name,base in [("Chrome",chrome),("Edge",edge)]:
            out.append((name,base/"Default/History"))
            try: out += [(name,p/"History") for p in base.glob("Profile *")]
            except Exception: pass
        try: out += [("Firefox",p) for p in firefox.glob("*/places.sqlite")]
        except Exception: pass
        return out

    def ai_label(self,url):
        host=(urlparse(url).hostname or "").lower()
        m={"chatgpt.com":"ChatGPT","chat.openai.com":"ChatGPT",
           "gemini.google.com":"Gemini","claude.ai":"Claude",
           "copilot.microsoft.com":"Microsoft Copilot","perplexity.ai":"Perplexity",
           "poe.com":"Poe","character.ai":"Character.AI"}
        return m.get(host)

    def read_recent(self,limit=30):
        rows=[]; seen=set()
        for browser,src in self.sources():
            db=self.copydb(src)
            if not db: continue
            try:
                con=sqlite3.connect(db)
                if browser=="Firefox":
                    q="SELECT url,title FROM moz_places WHERE url IS NOT NULL ORDER BY last_visit_date DESC LIMIT 50"
                else:
                    q="SELECT url,title FROM urls ORDER BY last_visit_time DESC LIMIT 50"
                for url,title in con.execute(q).fetchall():
                    key=(url,title)
                    if key in seen: continue
                    seen.add(key)
                    rows.append({"browser":browser,"host":urlparse(url).hostname or "",
                                  "url":url,"title":title or "",
                                  "ai_service":self.ai_label(url)})
                con.close()
            except Exception: pass
            try: db.unlink(missing_ok=True)
            except Exception: pass
        rows.sort(key=lambda x:x["ai_service"] is not None, reverse=True)
        return rows[:limit]
