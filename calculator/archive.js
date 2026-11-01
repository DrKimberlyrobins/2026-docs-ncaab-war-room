'use strict';
window.DocArchive=(()=>{
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=x=>Number.isFinite(x)?x.toFixed(1):'Unavailable';
 const signed=x=>Number.isFinite(x)?(x>0?'+':'')+x.toFixed(1):'Unavailable';
 const stamp=x=>new Date(x).toLocaleString('en-US',{timeZone:'America/Chicago',timeZoneName:'short'});
 const records=new Map();let index=[],health='Archive has not loaded.';
 async function json(path){const r=await fetch('../data/archive/'+path,{cache:'no-store',signal:AbortSignal.timeout(25000)});if(!r.ok)throw Error('Saved evidence is not available yet');return r.json();}
 async function load(){try{const d=await json('index.json');if(!Array.isArray(d.games))throw Error('Invalid archive index');index=d.games;health=`${index.length} pregame receipts saved across devices · checked ${stamp(d.updatedAt)}`;try{const h=await json('health.json');if(h.status!=='READY')health+=' · Archive update '+h.status;}catch{health+=' · Archive health unavailable';}}catch(e){health=e.message;}}
 function badge(id){const g=index.find(x=>x.id===String(id));return g?`<p><b>Pregame receipt saved</b> · ${esc(stamp(g.savedAt))} · <a href="#saved">View saved evidence & results</a></p>`:'<p class="muted">Awaiting automatic pregame save. Games already started are never saved retroactively.</p>';}
 function settle(n){return n>0?'WIN':n<0?'LOSS':'PUSH';}
 function marketRows(s,r,extra){
  const m=s.kambi||{periods:{},fetchedAt:s.savedAt};if(!s.kambi&&!Object.values(extra||{}).some(p=>Object.keys(p).length))return `<p>${esc(s.marketStatus)}</p>`;
  const g=s.matchup,names={[g.awayId]:g.awayName,[g.homeId]:g.homeName};
  let rows='';
  for(const period of ['half','full'])for(const kind of ['spread','total','moneyline']){
   const offer=m.periods?.[period]?.[kind]||extra?.[period]?.[kind];
   if(!offer){rows+=`<tr><td>${period==='half'?'1H':'Full game'}</td><td>${kind}</td><td colspan="2">NO SAVED MARKET</td></tr>`;continue;}
   for(const o of offer.outcomes){
    const actual=r?.[period],home=String(o.teamId)===String(g.homeId);
    let outcome='Awaiting actual result';
    if(actual){let delta;if(kind==='total')delta=o.side==='over'?actual.total-o.line:o.line-actual.total;else delta=(home?actual.homeMargin:-actual.homeMargin)+(kind==='spread'?o.line:0);outcome=settle(delta);}
    const label=names[o.teamId]||o.side;
    rows+=`<tr><td>${period==='half'?'1H':'Full game'}</td><td>${kind}</td><td>${esc(label)}${kind==='moneyline'?'':' '+(kind==='spread'?signed(o.line):fmt(o.line))} (${o.price>0?'+':''}${esc(o.price)})${offer.quoteFetchedAt?'<br><small>Later-opened market saved '+esc(stamp(offer.quoteSavedAt))+'</small>':''}</td><td>${outcome}</td></tr>`;
   }
  }
  return `<h3>Saved Kambi lines & results</h3><p>${s.kambi?'Original quotes retrieved '+esc(stamp(m.fetchedAt))+'.':'Market quotes first became available after the projection was saved.'} Later-opened markets are saved separately before tipoff and labeled; original prices remain unchanged. Each offered side is graded separately; these are market outcomes, not recorded wagers or recommendations. A tied 1H moneyline is a push for this draw-no-bet market.</p><div class="scroll"><table><tr><th>Period</th><th>Market</th><th>Frozen line & American price</th><th>Result</th></tr>${rows}</table></div>`;
 }
 function comparison(record){
  const s=record.snapshot,r=record.result,g=s.matchup;
  let rows='';for(const [key,label,model] of [['half','1H',g.firstHalf],['full','Full game',g.model]]){
   const a=r?.[key];
   for(const [field,name] of [['away',g.awayName],['home',g.homeName],['total','Total'],['homeMargin',g.homeName+' margin']])rows+=`<tr><td>${label}</td><td>${esc(name)}</td><td>${fmt(model?.[field])}</td><td>${fmt(a?.[field])}</td><td>${model&&a?signed(a[field]-model[field]):'—'}</td></tr>`;
  }
  return `<p><b>Frozen pregame receipt</b> · saved ${esc(stamp(s.savedAt))} · ${r?'Final result retrieved '+esc(stamp(r.fetchedAt)):'Awaiting completed game'}</p><p>Saved scores and prices stay unchanged. Error = actual minus projected; positive means the actual value was higher. Accuracy is separate from whether a sportsbook side won.</p><div class="scroll"><table><tr><th>Period</th><th>Measure</th><th>Saved projection</th><th>Actual</th><th>Error</th></tr>${rows}</table></div>${r&&!r.half?'<p>Actual first-half score unavailable; 1H grading remains pending.</p>':''}${marketRows(s,r,record.additionalMarkets)}${window.DocReports?.evidence(record.reportEvidence)||''}${r?`<p><a href="${esc(r.sourceUrl)}" target="_blank" rel="noopener">ESPN final-score evidence</a></p>`:''}<details><summary>Original projection, timing samples & source evidence</summary><pre>${esc(JSON.stringify({snapshot:s,additionalMarkets:record.additionalMarkets},null,2))}</pre></details>`;
 }
 async function render(mode,date,filter,container){
  const now=new Date(),q=filter.toLowerCase();
  const games=index.filter(g=>(mode!=='previous'||new Date(g.tipoff)<now)&&(!date||g.date===date)&&(g.awayName+' '+g.homeName).toLowerCase().includes(q)).sort((a,b)=>new Date(b.tipoff)-new Date(a.tipoff));
  container.innerHTML=`<article><p>${esc(health)}</p><p>Automatic first pregame save; no manual entry. Original projections, model settings, source timing samples, Game Room baselines, and available Kambi prices are retained. Games missed before tipoff are not reconstructed.</p></article>`+games.map(g=>`<article><h2>${esc(g.awayName)} vs. ${esc(g.homeName)}</h2><p>${esc(stamp(g.tipoff))} · ${g.final?'Final':'Result pending'}</p><details data-receipt="${esc(g.id)}"><summary>Saved projection vs. actual · open comparison</summary><div class="receipt-body">Loading saved receipt…</div></details></article>`).join('')+(games.length?'':'<article>No saved pregame receipts for this selection yet.</article>');
  container.querySelectorAll('[data-receipt]').forEach(el=>{el.ontoggle=async()=>{if(!el.open)return;const body=el.querySelector('.receipt-body'),id=el.dataset.receipt;try{const record=await json('games/'+encodeURIComponent(id)+'.json');if(String(record.snapshot?.id)!==id)throw Error('Receipt identity check failed');records.set(id,record);body.innerHTML=comparison(record);}catch(e){body.textContent=e.message;}};});
 }
 return {load,badge,render,comparison,settle};
})();
