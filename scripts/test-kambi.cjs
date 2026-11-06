const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const now=new Date(),date=now.toISOString().slice(0,10),future=new Date(+now+3600000).toISOString();
const outcome=(teamId,line,price)=>({teamId,line,price});
const markets={full:{},half:{spread:{outcomes:[outcome('87',3.5,-109),outcome('222',-3.5,-120)]},total:{outcomes:[{side:'over',line:67.5,price:-122},{side:'under',line:67.5,price:-108}]},moneyline:{outcomes:[outcome('87',null,180),outcome('222',null,-240)]}}};
const game={fetchedAt:now.toISOString(),start:future,state:'NOT_STARTED',sourceUrl:'https://example.com',periods:markets};
const snapshot={date,offering:'pivusmsrl-bil',market:'US-MS',games:{g:game}};
const ctx=vm.createContext({window:{},Date,Number,String,Map,JSON,AbortSignal,fetch:async u=>({ok:true,json:async()=>u.includes('health')?{status:'READY'}:snapshot})});
vm.runInContext(fs.readFileSync('kambi.js','utf8'),ctx);
(async()=>{const k=ctx.window.DocKambi;await k.load(date);const p={half:{homeMargin:4,total:67.7}};const frozen=JSON.stringify(p);
 let html=k.render('g',date,p,'87','222','Notre Dame','Villanova');assert.match(html,/\+0.5 points toward Villanova/);assert.match(html,/\+0.2 points vs total/);assert.match(html,/-240/);assert.match(html,/NO MARKET/);assert.equal(JSON.stringify(p),frozen);
 game.fetchedAt=new Date(+now-7200000).toISOString();html=k.render('g',date,p,'87','222','Notre Dame','Villanova');assert.match(html,/Comparison withheld/);assert.ok(!html.includes('+0.5 points toward'));
 game.fetchedAt=now.toISOString();game.start=new Date(+now-1000).toISOString();assert.match(k.render('g',date,p,'87','222','Notre Dame','Villanova'),/TIPOFF HAS PASSED/);
 assert.match(k.render('missing',date,p),/NO EXACT KAMBI EVENT MATCH/);console.log('Kambi comparison arithmetic, isolation and stale/tipoff guards passed.');})().catch(e=>{console.error(e);process.exitCode=1;});

async function verifyArchiveAndEntry(){
 const first='20261106T211315984033Z',last='20261106T212238821916Z';
 const records=new Map(),panel={textContent:''},cell={querySelector:()=>panel};
 let listener;
 const button={dataset:{outcome:'over'},closest:()=>cell};
 const offered={...markets.half.total,id:'offer',criterionId:'criterion',label:'Total Points - 1st Half',
  outcomes:markets.half.total.outcomes.map(o=>({...o,id:o.side}))};
 const rolling={...snapshot,games:{g:{...game,eventId:'event',start:future,
  fetchedAt:now.toISOString(),state:'NOT_STARTED',periods:{half:{total:offered}}}}};
 const archive={...rolling,evidenceType:'observed_pregame_quotes'};
 const browser=vm.createContext({window:{localStorage:{getItem:key=>records.get(key),setItem:(key,value)=>records.set(key,value)}},
  document:{addEventListener:(_,cb)=>listener=cb,querySelectorAll:()=>[button]},AbortSignal,
  fetch:async u=>({ok:true,json:async()=>u.endsWith('index.json')?{firstByGame:{g:first},latestByGame:{g:last}}:
   u.includes('history')?archive:u.includes('health')?{status:'READY'}:rolling})});
 vm.runInContext(fs.readFileSync('kambi.js','utf8'),browser);
 const k=browser.window.DocKambi,event={name:'Test game',date:future,status:{type:{state:'pre'}}};
 await k.load(date);
 const html=k.render('g',date,{half:{away:32,home:36,total:68}},'87','222','ND','Nova',event);
 assert.match(html,/First observed/);
 assert.match(html,/32.0 – 36.0/);
 assert.equal((html.match(/67\.5 \(-122\)/g)||[]).length,3);
 button.dataset.kambiEntry=html.match(/data-kambi-entry="([^"]+)" data-outcome="over"/)[1].replaceAll('&quot;','"');
 listener({target:{closest:()=>button}});
 const original=[...records.values()][0],entry=Object.values(JSON.parse(original))[0];
 assert.equal(entry.outcome.price,-122);
 assert.equal(entry.outcome.line,67.5);
 assert.equal(entry.projection.total,68);
 assert.match(cell.textContent,/CLV pending/);
 listener({target:{closest:()=>button}});
 assert.equal([...records.values()][0],original);
 assert.match(panel.textContent,/already saved/);
 assert.match(k.render('g',date,{},'87','222','ND','Nova',event),/CLV pending/);
 event.status.type.state='in';
 assert.doesNotMatch(k.render('g',date,{},'87','222','ND','Nova',event),/data-kambi-entry/);
}
verifyArchiveAndEntry().catch(e=>{console.error(e);process.exitCode=1;});
