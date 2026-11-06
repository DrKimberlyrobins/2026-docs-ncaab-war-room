/* Market evidence only. This module never writes a projection. */
'use strict';
window.DocKambi=(()=>{
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const one=x=>Number.isFinite(x)?x.toFixed(1):'Unavailable';
 const signed=x=>Number.isFinite(x)?(x>0?'+':'')+x.toFixed(1):'Unavailable';
 const odds=x=>x>0?'+'+x:String(x);
 const stamp=x=>new Date(x).toLocaleString('en-US',{timeZone:'America/Chicago',timeZoneName:'short'});
 const snapshots=new Map();let status='Kambi has not loaded.';
 async function load(date,prefix=''){
  try{const [r,h]=await Promise.all([fetch(prefix+'data/kambi/'+date+'.json',{cache:'no-store',signal:AbortSignal.timeout(25000)}),fetch(prefix+'data/kambi/health.json',{cache:'no-store',signal:AbortSignal.timeout(25000)})]);if(!r.ok)throw Error('No market snapshot for this date');const d=await r.json();if(d.date!==date||!d.games)throw Error('Market snapshot failed date check');snapshots.set(date,d);status='';if(h.ok){const health=await h.json();if(health.status!=='READY')status='Latest Kambi refresh: '+health.status+' · '+(health.message||'some event markets unavailable');}}
  catch(e){status=e.message; snapshots.delete(date);}
 }
 async function loadHistory(date){
  const panel=document.getElementById('market-history');
  if(!panel)return;
  panel.dataset.date=date;
  panel.textContent='Loading captured Kambi quotes for '+date+'…';
  try{
   const base='data/kambi/history/'+date+'/';
   const r=await fetch(base+'index.json',{cache:'no-store',signal:AbortSignal.timeout(10000)});
   if(!r.ok)throw Error();
   const {latestByGame}=await r.json();
   const files=[...new Set(Object.values(latestByGame))].filter(x=>/^\d{8}T\d{12}Z$/.test(x)).sort().reverse();
   if(!files.length)throw Error();
   if(panel.dataset.date!==date)return;
   panel.innerHTML='<p>'+Object.keys(latestByGame).length+' games with archived pregame quotes on '+esc(date)+'.</p>'+
    '<ul>'+files.map(key=>'<li><a href="'+base+key+'.json" target="_blank" rel="noopener">View captured lines and prices · '+esc(stamp(key.replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2}).*Z$/,'$1-$2-$3T$4:$5:$6Z')))+'</a></li>').join('')+'</ul>';
  }catch{if(panel.dataset.date===date)panel.textContent='No archived Kambi quotes are available for '+date+'.';}
 }
 function render(id,date,projection,awayId,homeId,awayName,homeName){
  const d=snapshots.get(date),g=d?.games?.[id];
  if(!g||g.error)return `<section class="kambi"><h3>Kambi sportsbook comparison</h3><p>${esc(g?.error||status||'NO EXACT KAMBI EVENT MATCH')}</p></section>`;
  awayId=awayId||g.awayId;homeId=homeId||g.homeId;
  const age=Date.now()-new Date(g.fetchedAt).getTime(),stale=!Number.isFinite(age)||age>3600000;
  const started=Date.now()>=new Date(g.start).getTime();
  const names={[awayId]:awayName,[homeId]:homeName};
  const rows=['half','full'].map(period=>{
   const p=projection?.[period],markets=g.periods?.[period]||{};
   return ['spread','total','moneyline'].map(kind=>{
    const m=markets[kind];if(!m)return `<tr><td>${period==='half'?'1H':'Full game'}</td><td>${kind}</td><td colspan="3">NO MARKET</td></tr>`;
    const prices=m.outcomes.map(o=>`${names[o.teamId]||o.side}${kind==='moneyline'?'':' '+(kind==='total'?one(o.line):signed(o.line))} (${odds(o.price)})`).join(' · ');
    let model='No calibrated win probability',difference='—';
    if(kind==='total'){model=one(p?.total);if(p&&Number.isFinite(p.total))difference=signed(p.total-m.outcomes[0].line)+' points vs total';}
    if(kind==='spread'){
     const home=m.outcomes.find(o=>o.teamId===String(homeId));model=p?esc(homeName)+' '+signed(p.homeMargin)+' margin':'Unavailable';
     if(p&&home&&Number.isFinite(p.homeMargin))difference=signed(p.homeMargin+home.line)+' points toward '+esc(homeName);
    }
    if(stale||started)difference='Comparison withheld';
    return `<tr><td>${period==='half'?'1H':'Full game'}</td><td>${kind}</td><td>${esc(prices)}</td><td>${model}</td><td>${difference}</td></tr>`;
   }).join('');
  }).join('');
  return `<section class="kambi"><h3>Kambi sportsbook comparison</h3><p>${projection?.full?.possessions!==undefined?'KenPom-based model':'Game Room scoring baseline'} shown above; sportsbook prices never change these projections.</p><p class="muted">Kambi · offering ${esc(d.offering)} · ${esc(d.market)} · retrieved ${esc(stamp(g.fetchedAt))} · ${esc(g.state)}${stale?' · SNAPSHOT OVER 1 HOUR OLD':''}${started?' · SCHEDULED TIPOFF HAS PASSED':''}</p>${status?'<p>'+esc(status)+'</p>':''}<div class="scroll"><table><tr><th>Period</th><th>Market</th><th>Kambi line (American odds)</th><th>Our projection</th><th>Point difference</th></tr>${rows}</table></div><p class="muted">Positive spread difference favors ${esc(homeName)}; negative favors ${esc(awayName)}. Differences are arithmetic comparisons, not validated betting edges. Moneyline prices do not imply a model win probability. Snapshots refresh on a 30-minute schedule; they are not live quotes.</p><details><summary>Kambi market evidence</summary><p><a href="${esc(g.sourceUrl)}" target="_blank" rel="noopener">Kambi event ${esc(g.eventId)}</a></p><pre>${esc(JSON.stringify(g.periods,null,2))}</pre></details></section>`;
 }
 return {load,loadHistory,render};
})();
