const token=new URLSearchParams(location.search).get("token")||"";
const $=id=>document.getElementById(id);
const hdr={"X-MLDoctor-Token":token,"Content-Type":"application/json"};
let unit="runs identical",liveCap=8;
function done(step){const el=document.querySelector(`[data-step="${step}"]`);if(el)el.classList.add("done");}
function svg(el,ev){
  if(!ev||!ev.loss_curves){el.textContent="—";return;}
  const cs=ev.loss_curves.flat().filter(v=>v!==null&&isFinite(v));
  const mx=Math.max(...cs,1),mn=Math.min(...cs,0),W=480,H=140;
  const lines=ev.loss_curves.map((c,i)=>{const pts=c.map((y,j)=>`${(j/Math.max(c.length-1,1))*W},${H-((y-mn)/Math.max(mx-mn,1e-9))*H}`).join(" ");return `<polyline fill="none" stroke="hsl(${i*70},70%,35%)" points="${pts}"/>`;}).join("");
  const hashes=ev.hash_fingerprints.map((r,i)=>`run ${i}: ${r.join(" ")}`).join("<br>");
  el.innerHTML=`<svg width="${W}" height="${H}" style="background:#f4f4f4">${lines}</svg><div style="font-family:ui-monospace,monospace;font-size:12px">${hashes}</div>`;
}
function onEvent(e){
  done(e.type);$("status").textContent=e.type;
  if(e.type==="baseline_completed")svg($("evidence-before"),e.evidence);
  if(e.type==="verification_started")unit=e.mode==="seeds"?"seeds finite":"runs identical";
  if(e.type==="verify_progress")$("counter").textContent=`${e.n_done} / ${e.n_total} ${unit} (${e.n_failed} failed)`;
  if(e.type==="diagnosed")$("hypo").textContent=`${e.diagnosis.culprit} — ${e.diagnosis.fix_plan} (${e.diagnosis.reason})`;
  if(e.type==="patch_applied")$("diff").textContent=e.diff||"—";
  if(e.type==="verification_completed"){svg($("evidence-after"),e.evidence);$("counter").textContent=`${e.k} / ${e.k} ${unit}`;$("verdict").textContent=`${e.verdict} — ${e.reason}`;$("report").style.display="inline";$("report").href=`/api/report?token=${encodeURIComponent(token)}`;}
  if(e.type==="pipeline_completed"){$("verdict").textContent=e.verdict;$("status").textContent="done";}
  if(e.type==="pipeline_failed"){$("verdict").textContent="ERROR: "+e.error;}
}
fetch("/api/state",{headers:hdr}).then(r=>r.json()).then(s=>{
  if(s.live_configured){$("live").disabled=false;liveCap=s.call_cap||8;}
  $("mock-badge").textContent=s.live_configured?"MOCK (live available)":"MOCK — no live calls";
}).catch(()=>{});
$("live").onchange=()=>{
  if($("live").checked&&!confirm(`Enable LIVE model calls? Per-run call cap: ${liveCap}. Calls will use the server-configured model.`)){$("live").checked=false;return;}
  $("mock-badge").textContent=$("live").checked?"LIVE":"MOCK";
};
const es=new EventSource(`/api/events?token=${encodeURIComponent(token)}`);
es.onmessage=m=>onEvent(JSON.parse(m.data));
$("run").onclick=async()=>{
  document.querySelectorAll("#tracker li").forEach(li=>li.classList.remove("done"));
  $("counter").textContent="0 / 0";
  const body={script:$("script").value,k:+$("k").value,verify_k:$("verifyk").value?+$("verifyk").value:null,live:$("live").checked};
  const r=await fetch("/api/run",{method:"POST",headers:hdr,body:JSON.stringify(body)});
  $("status").textContent=r.ok?"running":("error "+r.status+": "+await r.text());
};
