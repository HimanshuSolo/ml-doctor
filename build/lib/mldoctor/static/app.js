const token=new URLSearchParams(location.search).get("token")||"";
const $=id=>document.getElementById(id);
const hdr={"X-MLDoctor-Token":token,"Content-Type":"application/json"};
function done(step){const el=document.querySelector(`[data-step="${step}"]`);if(el)el.classList.add("done");}
function onEvent(e){
  done(e.type);$("status").textContent=e.type;
  if(e.type==="diagnosed")$("hypo").textContent=`${e.diagnosis.culprit} — ${e.diagnosis.fix_plan} (${e.diagnosis.reason})`;
  if(e.type==="patch_applied")$("diff").textContent=e.diff||"—";
  if(e.type==="verification_completed"){$("counter").textContent=e.k;$("verdict").textContent=`${e.verdict} — ${e.reason}`;}
  if(e.type==="pipeline_completed"){$("verdict").textContent=e.verdict;$("status").textContent="done";}
  if(e.type==="pipeline_failed"){$("verdict").textContent="ERROR: "+e.error;}
}
const es=new EventSource(`/api/events?token=${encodeURIComponent(token)}`);
es.onmessage=m=>onEvent(JSON.parse(m.data));
$("run").onclick=async()=>{
  document.querySelectorAll("#tracker li").forEach(li=>li.classList.remove("done"));
  $("counter").textContent="0";
  const body={script:$("script").value,k:+$("k").value,verify_k:$("verifyk").value?+$("verifyk").value:null};
  const r=await fetch("/api/run",{method:"POST",headers:hdr,body:JSON.stringify(body)});
  $("status").textContent=r.ok?"running":("error "+r.status+": "+await r.text());
};
