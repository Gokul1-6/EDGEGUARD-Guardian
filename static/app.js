let timer;
const $=id=>document.getElementById(id);
function esc(x){return String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));document.querySelectorAll("nav button").forEach(x=>x.classList.remove("active"));$(b.dataset.t).classList.add("active");b.classList.add("active")});
function dur(s){s=Number(s||0);return s>=3600?`${Math.floor(s/3600)}h ${Math.floor(s%3600/60)}m`:`${Math.floor(s/60)}m`}
async function cfg(){return await (await fetch("/api/config")).json()}
async function refresh(){
 const d=await (await fetch("/api/status")).json(),l=d.latest;
 $("proc").textContent=(l.processes||[]).length;
 $("aisvc").textContent=(l.ai||[]).length?l.ai.map(x=>x.service).join(", "):"No active AI service";
 if(l.battery?.available){$("bat").textContent=l.battery.percent+"%";$("power").textContent=l.battery.state}
 $("ailist").innerHTML=(l.ai||[]).map(x=>`<div class=item><span><b>${esc(x.service)}</b><br><small>${esc(x.process)} • Model: ${esc(x.model)}</small></span><span>ACTIVE</span></div>`).join("")||'<span class=muted>No local AI process observed.</span>';
 $("sessions").innerHTML=(d.sessions||[]).map(x=>`<div class=item><span><b>${esc(x.service)}</b><br><small>${esc(x.started)}</small></span><span>${dur(x.duration_seconds)}</span></div>`).join("")||'<span class=muted>No completed sessions.</span>';
 $("weblist").innerHTML=(l.websites||[]).map(x=>`<div class=item><span><b>${esc(x.title)}</b><br><small>${esc(x.host)} • ${esc(x.browser)}</small></span><span>${x.ai_service?esc(x.ai_service):"WEB"}</span></div>`).join("")||'<span class=muted>No readable browser history found.</span>';
 $("live").innerHTML=(d.events||[]).slice(0,10).map(x=>`<div class=item><span><b>${esc(x.kind)}</b><br><small>${esc(x.ts)} • ${esc(x.app)}</small></span><span>${esc(x.risk)}</span></div>`).join("");
 $("eventslist").innerHTML=(d.events||[]).map(x=>`<div class=item><span><b>${esc(x.kind)}</b><br><small>${esc(x.ts)} • ${esc(x.app)}</small><br>${esc(x.detail)}</span><span>${esc(x.risk)}</span></div>`).join("")||'<span class=muted>No events.</span>';
 const c=await cfg();$("rules").textContent=JSON.stringify(c.rules||[],null,2);$("schedules").textContent=JSON.stringify(c.schedules||[],null,2);
 if(!timer)timer=setInterval(refresh,Math.max(2,Number(c.monitoring.dashboard_refresh_seconds||5))*1000);
}
async function rule(){if(!$("rt").value.trim())return;await fetch("/api/rule",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({target:$("rt").value,type:$("rty").value,action:$("ra").value})});$("rt").value="";refresh()}
async function sched(){await fetch("/api/schedule",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:$("sn").value,start:$("ss").value,end:$("se").value,action:$("sa").value,days:["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]})});refresh()}
async function clearEvents(){if(confirm("Clear local events?")){await fetch("/api/clear-events",{method:"POST"});refresh()}}
async function save(){let c=await cfg();c.monitoring.system_poll_seconds=Number($("sp").value);c.monitoring.browser_history_poll_seconds=Number($("bp").value);c.monitoring.dashboard_refresh_seconds=Number($("dp").value);await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(c)});clearInterval(timer);timer=null;refresh()}
(async()=>{let c=await cfg();$("sp").value=c.monitoring.system_poll_seconds;$("bp").value=c.monitoring.browser_history_poll_seconds;$("dp").value=c.monitoring.dashboard_refresh_seconds;refresh()})();