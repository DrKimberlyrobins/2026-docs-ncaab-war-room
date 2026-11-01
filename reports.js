/* Public reporting evidence; deliberately has no access to projection setters. */
'use strict';
window.DocReports=(()=>{
 const data=new Map();let failure='Reports have not loaded.';
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const safe=u=>/^https?:\/\//i.test(u||'')?u:'#';
 const stamp=x=>x?.length===10?x+' (publication date only)':new Date(x).toLocaleString('en-US',{timeZone:'America/Chicago',timeZoneName:'short'});
 function article(a,saved=false){
  const check=a.reviewedAt||a.retrievedAt;
  return `<div class="report-item"><h4><a href="${esc(safe(a.url))}" target="_blank" rel="noopener">${esc(a.title)}</a></h4><p class="muted">${esc(a.publisher)} · ${esc(a.kind)} · ${esc(a.author||'Byline unavailable')}<br>Published ${esc(stamp(a.publishedAt))}${check?'<br>'+(a.reviewedAt?'Notes reviewed ':'Feed retrieved ')+esc(stamp(check)):''}${saved&&a.savedAt?'<br>Saved before tipoff '+esc(stamp(a.savedAt)):''}</p>${a.notes?.length?'<ul>'+a.notes.map(n=>`<li><b>${esc(n.category)} · ${esc(n.status)}:</b> ${esc(n.text)}</li>`).join('')+'</ul>':'<p>Headline only — article contents and player status have not been reviewed by this panel.</p>'}</div>`;
 }
 async function load(date,prefix=''){
  try{const r=await fetch(prefix+'data/reports/'+date+'.json',{cache:'no-store',signal:AbortSignal.timeout(25000)});if(!r.ok)throw Error('Prepared reports unavailable');const d=await r.json();if(d.date!==date||!d.games)throw Error('Reports date check failed');data.set(date,d);failure='';}catch(e){data.delete(date);failure=e.message;}
 }
 function render(id,date){
  const d=data.get(date),g=d?.games?.[id];if(!g)return `<section><h3>Pregame Reports</h3><p>${esc(failure||'No connected public reporting found for this matchup.')}</p></section>`;
  const errors=(d.sources||[]).filter(s=>s.status!=='READY'),stale=Date.now()-new Date(d.checkedAt)>21600000;
  const items=g.articles||[],reviewed=items.filter(a=>a.notes?.length);
  return `<section class="pregame-reports"><h3>Pregame Reports</h3><p>${reviewed.length} reviewed source summaries · ${items.length} public reports · checked ${esc(stamp(d.checkedAt))}${stale?' · FEED CHECK OVER 6 HOURS OLD':''}</p><p>Reports do not change our scoring projection. Writer expectations are separate from official team information. Confirmed starting fives and minutes are not established by a preview or headline.</p>${errors.length?'<p>Some sources could not refresh: '+esc(errors.map(s=>s.name).join(', '))+'. Older items keep their original retrieval times.</p>':''}${!g.localSourceTeams?.length?'<p>No dedicated local/team feed connected for these teams yet; available national reporting is shown.</p>':''}${reviewed.map(a=>article(a)).join('')}${items.some(a=>!a.notes?.length)?'<details><summary>Additional automatically collected headlines</summary>'+items.filter(a=>!a.notes?.length).map(a=>article(a)).join('')+'</details>':''}${items.length?'':'<p>No recent report found in the connected sources. This does not confirm that players are healthy or available.</p>'}<p class="muted">${esc(g.coverage)} Reviewed summaries keep their review date; newly published feed items remain headlines until reviewed.</p></section>`;
 }
 function evidence(e){return e?.articles?.length?`<details><summary>Saved pregame reports & source evidence</summary><p>These reports were retained before tipoff. Later reports cannot replace this evidence.</p>${e.articles.map(a=>article(a,true)).join('')}</details>`:'';}
 return {load,render,evidence,article};
})();
