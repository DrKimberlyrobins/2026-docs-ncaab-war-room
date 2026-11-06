/* Market evidence only. This module never writes a projection. */
'use strict';
window.DocKambi=(()=>{
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const one=x=>Number.isFinite(x)?x.toFixed(1):'Unavailable';
 const signed=x=>Number.isFinite(x)?(x>0?'+':'')+x.toFixed(1):'Unavailable';
 const odds=x=>x>0?'+'+x:String(x);
 const stamp=x=>new Date(x).toLocaleString('en-US',{timeZone:'America/Chicago',timeZoneName:'short'});
 const snapshots=new Map(),histories=new Map();let status='Kambi has not loaded.';
 async function readHistory(date,prefix){
  const base=prefix+'data/kambi/history/'+date+'/';
  const read=async file=>{const response=await fetch(base+file,{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error('Archive unavailable');return response.json();};
  try{
   const index=await read('index.json');
   const first=index.firstByGame||{},last=index.latestByGame||{};
   const keys=[...new Set([...Object.values(first),...Object.values(last)])].filter(key=>/^\d{8}T\d{12}Z$/.test(key));
   const files=new Map();
   for(let i=0;i<keys.length;i+=6)await Promise.all(keys.slice(i,i+6).map(async key=>{
    try{const data=await read(key+'.json');if(data.date===date&&data.evidenceType==='observed_pregame_quotes')files.set(key,data);}catch{}
   }));
   const identity=files.values().next().value;
   if(!identity)return;
   const records=pointers=>new Map(Object.entries(pointers).flatMap(([id,key])=>{
    const file=files.get(key),record=file?.games?.[id];
    return record&&file.offering===identity.offering&&file.market===identity.market?[[id,record]]:[];
   }));
   histories.set(date,{first:records(first),last:records(last),offering:identity.offering,region:identity.market});
  }catch{}
 }
 async function load(date,prefix=''){
  const archive=readHistory(date,prefix);
  try{const [r,h]=await Promise.all([fetch(prefix+'data/kambi/'+date+'.json',{cache:'no-store',signal:AbortSignal.timeout(25000)}),fetch(prefix+'data/kambi/health.json',{cache:'no-store',signal:AbortSignal.timeout(25000)})]);if(!r.ok)throw Error('No market snapshot for this date');const d=await r.json();if(d.date!==date||!d.games)throw Error('Market snapshot failed date check');snapshots.set(date,d);status='';if(h.ok){const health=await h.json();if(health.status!=='READY')status='Latest Kambi refresh: '+health.status+' · '+(health.message||'some event markets unavailable');}}
  catch(e){status=e.message; snapshots.delete(date);}
  await archive;
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
 const entryKey='docs-ncaab-kambi-paper-entries-v1';
 const tickets=new Map();
 const readEntries=()=>{
  const rows=JSON.parse(window.localStorage?.getItem(entryKey)||'{}');
  if(!rows||Array.isArray(rows)||typeof rows!=='object')throw Error('Saved entry storage is unavailable.');
  return rows;
 };
 function canSave(ticket){
  const {event,quote}=ticket;
  const now=Date.now(), seen=Date.parse(quote.fetchedAt);
  return event?.status?.type?.state==='pre' && quote.state==='NOT_STARTED' &&
   Number.isFinite(seen) && seen<=now && now-seen<=3600000 &&
   now<Math.min(Date.parse(event.date),Date.parse(quote.start)) &&
   snapshots.get(ticket.date)?.games?.[ticket.id]===quote;
 }
 function saveEntry(ticket,outcomeId){
  if(!canSave(ticket))throw Error('The quote is stale, changed, or past tipoff. Refresh the slate.');
  const market=ticket.quote.periods[ticket.period][ticket.kind];
  const outcome=market.outcomes.find(o=>o.id===outcomeId);
  if(!outcome||!Number.isInteger(outcome.price)||Math.abs(outcome.price)<100||
     (ticket.kind!=='moneyline'&&!Number.isFinite(outcome.line)))throw Error('No valid line and price for this side.');
  const rows=readEntries();
  if(rows[ticket.key])throw Error('The original entry is already saved.');
  const {quote,event,period,kind,projection,offering,region,date,id}=ticket;
  const entry={date,id,game:event.name,scheduledTipoff:event.date,kambiEvent:quote.eventId,
   offering,region,period,kind,marketId:market.id,criterionId:market.criterionId,
   settlementLabel:market.label,outcome,source:quote.sourceUrl,observedAt:quote.fetchedAt,
   savedAt:new Date().toISOString(),projection:projection??null};
  rows[ticket.key]=entry;
  window.localStorage.setItem(entryKey,JSON.stringify(rows));
  return entry;
 }
 if(typeof document!=='undefined')document.addEventListener?.('click',event=>{
  const button=event.target.closest?.('button[data-kambi-entry]');
  if(!button)return;
  const ticket=tickets.get(button.dataset.kambiEntry);
  const cell=button.closest('td');
  try{
   if(!ticket)throw Error('Refresh the slate to load the quote.');
   const saved=saveEntry(ticket,button.dataset.outcome);
   for(const peer of document.querySelectorAll('button[data-kambi-entry]')){
    if(peer.dataset.kambiEntry!==button.dataset.kambiEntry)continue;
    const target=peer.closest('td');
    target.textContent=ticket.describe(saved.outcome)+' · saved '+stamp(saved.savedAt)+' · CLV pending';
   }
  }catch(e){cell.querySelector('[role=status]').textContent=e.message;}
 });
 function render(id,date,projection,awayId,homeId,awayName,homeName,event){
  const d=snapshots.get(date),g=d?.games?.[id],history=histories.get(date);
  const first=history?.first.get(String(id)),last=history?.last.get(String(id));
  const anchor=g&&!g.error?g:last||first;
  if(!anchor)return `<section class="kambi"><h3>Kambi sportsbook comparison</h3><p>${esc(g?.error||status||'NO EXACT KAMBI EVENT MATCH')}</p></section>`;
  awayId=awayId||anchor.awayId;homeId=homeId||anchor.homeId;
  const names={[awayId]:awayName,[homeId]:homeName};
  const quote=g&&!g.error?g:last;
  const age=Date.now()-Date.parse(quote?.fetchedAt);
  const stale=!Number.isFinite(age)||age<0||age>3600000;
  const started=Date.now()>=Math.min(Date.parse(anchor.start),Date.parse(event?.date||anchor.start)) ||
   (event&&event.status?.type?.state!=='pre');
  let entries={};
  try{entries=readEntries();}catch{}
  const sameMarket=(a,b,period,kind)=>a&&b&&a.eventId===b.eventId &&
   a.periods?.[period]?.[kind]?.criterionId===b.periods?.[period]?.[kind]?.criterionId &&
   a.periods?.[period]?.[kind]?.label===b.periods?.[period]?.[kind]?.label;
  const rows=['half','full'].flatMap(period=>['spread','total','moneyline'].map(kind=>{
   const p=projection?.[period],current=quote?.periods?.[period]?.[kind],opening=first?.periods?.[period]?.[kind];
   const offering=d?.offering||history?.offering,region=d?.market||history?.region;
   const key=JSON.stringify([id,anchor.eventId,offering,region,period,kind]);
   const saved=entries[key];
   if(!current&&!opening&&!saved)return `<tr><td>${period==='half'?'1H':'Full game'}</td><td>${kind}</td><td colspan="4">NO MARKET</td></tr>`;
   const describe=o=>`${names[o.teamId]||o.side||o.teamId}${kind==='moneyline'?'':' '+(kind==='total'?one(o.line):signed(o.line))} (${odds(o.price)})`;
   const prices=(market,record)=>market?market.outcomes.map(o=>esc(describe(o))).join('<br>')+'<br><small>'+esc(stamp(record.fetchedAt))+'</small>':'Unavailable';
   let model=p&&Number.isFinite(p.away)&&Number.isFinite(p.home)?`${one(p.away)} – ${one(p.home)}`:'Unavailable';
   let difference='';
   if(stale||started)difference='Comparison withheld';
   else if(current&&kind==='total'&&Number.isFinite(p?.total))difference=signed(p.total-current.outcomes[0].line)+' points vs total';
   else if(current&&kind==='spread'&&Number.isFinite(p?.homeMargin)){
    const home=current.outcomes.find(o=>o.teamId===String(homeId));
    if(home)difference=signed(p.homeMargin+home.line)+' points toward '+homeName;
   }
   const ticket={key,date,id,period,kind,quote,event,projection:p,offering,region,describe};
   const buttonKey=JSON.stringify([key,quote?.fetchedAt,p,event?.date,event?.status?.type?.state]);
   let entry=saved?esc(describe(saved.outcome))+'<br><small>Saved '+esc(stamp(saved.savedAt))+' · CLV pending</small>':'—';
   if(!saved&&current&&canSave(ticket)&&current.outcomes.every(o=>typeof o.id==='string')){
    tickets.set(buttonKey,ticket);
    entry=current.outcomes.map(o=>`<button type="button" data-kambi-entry="${esc(buttonKey)}" data-outcome="${esc(o.id)}">Save ${esc(describe(o))}</button>`).join(' ')+'<small role="status"></small>';
   }
   const firstComparable=history?.offering===offering&&history?.region===region&&(!current||sameMarket(first,quote,period,kind));
   return `<tr><td>${period==='half'?'1H':'Full game'}</td><td>${kind}</td><td>${esc(model)}<br><small>${esc(difference)}</small></td><td>${firstComparable?prices(opening,first):'Unavailable'}</td><td>${prices(current,quote)}</td><td>${entry}</td></tr>`;
  })).join('');
  return `<section class="kambi"><h3>Kambi sportsbook comparison</h3><p class="muted">Kambi · offering ${esc(d?.offering||history?.offering)} · ${esc(d?.market||history?.region)} ${stale?' · QUOTE UNAVAILABLE OR OVER 1 HOUR OLD':''}${started?' · TIPOFF HAS PASSED':''}</p><div class="scroll"><table><tr><th>Period</th><th>Market</th><th>Our projection</th><th>First observed</th><th>${started||quote===last||stale?'Last observed pregame':'Current snapshot'}</th><th>Our saved entry</th></tr>${rows}</table></div><p class="muted">Scores show away then home. Paper entries are saved on this browser. Observed quotes carry retrieval timestamps. Verified open, close and CLV are pending.</p><details><summary>Kambi market evidence</summary><pre>${esc(JSON.stringify(quote?.periods||{},null,2))}</pre></details></section>`;
 }
 return {load,loadHistory,render};
})();
