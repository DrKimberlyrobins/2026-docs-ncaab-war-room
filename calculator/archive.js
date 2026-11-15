'use strict';
window.DocArchive=(()=>{
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=x=>Number.isFinite(x)?x.toFixed(1):'Unavailable';
 const signed=x=>Number.isFinite(x)?(x>0?'+':'')+x.toFixed(1):'Unavailable';
 const stamp=x=>new Date(x).toLocaleString('en-US',{timeZone:'America/Chicago',timeZoneName:'short'});
 const records=new Map();let index=[],grades=null,health='Archive has not loaded.';
 async function json(path){const r=await fetch('../data/archive/'+path+'?refresh='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(25000)});if(!r.ok)throw Error('Saved evidence is not available yet');return r.json();}
 async function load(){try{const d=await json('index.json');if(!Array.isArray(d.games))throw Error('Invalid archive index');index=d.games;health=`${index.length} pregame receipts saved across devices · checked ${stamp(d.updatedAt)}`;try{const h=await json('health.json');if(h.status!=='READY')health+=' · Archive update '+h.status;}catch{health+=' · Archive health unavailable';}try{grades=await json('score-grades.json');}catch{grades=null;}}catch(e){health=e.message;}}
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
 function performance(date){
  const item=date?grades?.dates?.[date]:null, scores=item?.scores||(!date?grades?.summary:null);
  if(!scores)return '';
  const available=Object.entries(scores).filter(([,x])=>x.games);
  const replay=date?grades?.marketReplay?.[date]:null;
  return `<h3>Frozen forecast performance</h3><div class="scroll"><table><tr><th>Period</th><th>Games</th><th>Away team MAE</th><th>Home team MAE</th><th>Total MAE</th><th>Margin MAE</th></tr>${available.map(([p,x])=>`<tr><td>${p==='half'?'1H':'Full game'}</td><td>${esc(x.games)}</td><td>${fmt(x.mae.away)}</td><td>${fmt(x.mae.home)}</td><td>${fmt(x.mae.total)}</td><td>${fmt(x.mae.homeMargin)}</td></tr>`).join('')}</table></div>${replay?`<p>Kambi replay across ${esc(replay.quotedGames)} quoted games. Top candidate per game ${esc(replay.WIN)}–${esc(replay.LOSS)}–${esc(replay.PUSH)}, ${replay.netUnits>0?'+':''}${Number(replay.netUnits).toFixed(3)} units at recorded prices.</p>`:''}`;
 }
 function savedMarkets(record){
  const rows=record.decisionEvidence?.markets;
  if(!rows?.length)return '';
  const game=record.snapshot.matchup;
  const pct=n=>Number.isFinite(n)?fmt(n*100)+'%':'Pending';
  return `<details><summary>Saved Kambi research estimates and outcomes</summary><div class="scroll"><table><tr><th>Period</th><th>Selection</th><th>Price</th><th>Win probability</th><th>EV</th><th>Result</th></tr>${rows.map(x=>{
   const team=x.teamId===game.awayId?game.awayName:game.homeName;
   const label=x.kind==='spread'?team+' '+signed(x.line):x.side+' '+fmt(x.line);
   const a=record.result?.[x.period];
   const diff=!a?null:x.kind==='spread'?(x.teamId===game.awayId?-a.homeMargin:a.homeMargin)+x.line:(a.total-x.line)*(x.side==='over'?1:-1);
   return `<tr><td>${x.period==='half'?'1H':'Full game'}</td><td>${esc(label)}</td><td>${esc(x.price)}</td><td>${pct(x.probability)}</td><td>${pct(x.expectedValue)}</td><td>${diff===null?'Pending':settle(diff)}</td></tr>`;
  }).join('')}</table></div></details>`;
 }
 function savedExchange(record,check){
  const rows=record.kalshiEvidence?.markets;
  if(!rows?.length)return '';
  const cutoff=Math.min(Date.parse(record.snapshot.scheduledTipoff),Date.parse(check?.revisedTipoff||record.snapshot.scheduledTipoff));
  return `<details><summary>Saved Kalshi contract quotes</summary><p>Results derived from ESPN scores. Exchange settlements can differ under contract cancellation rules.</p><div class="scroll"><table><tr><th>Period</th><th>Contract</th><th>Answer</th><th>First ask</th><th>ESPN result</th></tr>${rows.filter(row=>Date.parse(row.quoteFetchedAt)<cutoff).map(row=>{
   const actual=record.result?.[row.period], margin=row.teamSide==='home'?actual?.homeMargin:-actual?.homeMargin;
   const value=row.kind==='total'?actual?.total:row.kind==='spread'?margin:actual?.[row.teamSide];
   return `<tr><td>${row.period==='half'?'1H':'Full game'}</td><td>${esc(row.label)}</td><td>${esc(row.answer)}</td><td>${fmt(row.ask*100)}¢</td><td>${actual?((value>row.line)===(row.answer==='yes')?'WIN':'LOSS'):'Pending'}</td></tr>`;
  }).join('')}</table></div></details>`;
 }
 function comparison(record,check){
  const s=record.snapshot,r=record.result,g=s.matchup;
  let rows='';for(const [key,label,model] of [['half','1H',g.firstHalf],['full','Full game',g.model]]){
   const a=r?.[key];
   for(const [field,name] of [['away',g.awayName],['home',g.homeName],['total','Total'],['homeMargin',g.homeName+' margin']])rows+=`<tr><td>${label}</td><td>${esc(name)}</td><td>${fmt(model?.[field])}</td><td>${fmt(a?.[field])}</td><td>${model&&a?signed(a[field]-model[field]):'—'}</td></tr>`;
  }
  return `<p><b>Frozen pregame receipt</b> · saved ${esc(stamp(s.savedAt))} · ${r?'Final result retrieved '+esc(stamp(r.fetchedAt)):'Awaiting completed game'}</p><p>Saved scores and prices stay unchanged. Error = actual minus projected; positive means the actual value was higher. Accuracy is separate from whether a sportsbook side won.</p><div class="scroll"><table><tr><th>Period</th><th>Measure</th><th>Saved projection</th><th>Actual</th><th>Error</th></tr>${rows}</table></div>${r&&!r.half?'<p>Actual first-half score unavailable; 1H grading remains pending.</p>':''}${check?.exclude?'<p>Excluded from forecast performance. The saved receipt is retained below.</p>':marketRows(s,r,record.additionalMarkets)+savedMarkets(record)+savedExchange(record,check)}${window.DocReports?.evidence(record.reportEvidence)||''}${r?`<p><a href="${esc(r.sourceUrl)}" target="_blank" rel="noopener">ESPN final-score evidence</a></p>`:''}<details><summary>Original projection, timing samples & source evidence</summary><pre>${esc(JSON.stringify({snapshot:s,additionalMarkets:record.additionalMarkets},null,2))}</pre></details>`;
 }
 async function render(mode,date,filter,container){
  const now=new Date(),q=filter.toLowerCase();
  const games=index.filter(g=>(mode!=='previous'||new Date(g.tipoff)<now)&&(!date||g.date===date)&&(g.awayName+' '+g.homeName).toLowerCase().includes(q)).sort((a,b)=>new Date(a.tipoff)-new Date(b.tipoff));
  container.innerHTML=`<article><p>${esc(health)}</p><p>Automatic first pregame save; no manual entry. Original projections, model settings, source timing samples, Game Room baselines, and available Kambi prices are retained. Games missed before tipoff are not reconstructed.</p>${performance(date)}</article>`+games.map(g=>`<article><h2>${esc(g.awayName)} vs. ${esc(g.homeName)}</h2><p>${esc(stamp(g.tipoff))} · ${g.scheduleCheck?esc(g.scheduleCheck.label)+(g.scheduleCheck.revisedTipoff?' · '+esc(stamp(g.scheduleCheck.revisedTipoff)):''):g.final?'Final':'Result pending'}</p><details data-receipt="${esc(g.id)}"><summary>Saved projection vs. actual · open comparison</summary><div class="receipt-body">Loading saved receipt…</div></details></article>`).join('')+(games.length?'':'<article>No saved pregame receipts for this selection yet.</article>');
  container.querySelectorAll('[data-receipt]').forEach(el=>{el.ontoggle=async()=>{if(!el.open)return;const body=el.querySelector('.receipt-body'),id=el.dataset.receipt;try{const record=await json('games/'+encodeURIComponent(id)+'.json');if(String(record.snapshot?.id)!==id)throw Error('Receipt identity check failed');records.set(id,record);body.innerHTML=comparison(record,index.find(x=>x.id===id)?.scheduleCheck);if(record.result?.full&&!index.find(x=>x.id===id)?.scheduleCheck){const heading=el.previousElementSibling;if(heading&&heading.tagName==='P')heading.textContent=stamp(record.snapshot.matchup?.date||record.snapshot.tipoff||new Date())+' · Final '+record.result.full.away+'–'+record.result.full.home;}}catch(e){body.textContent=e.message;}};if(date&&index.find(x=>x.id===el.dataset.receipt)?.final)el.open=true;});
 }
 return {load,badge,render,comparison,settle};
})();
