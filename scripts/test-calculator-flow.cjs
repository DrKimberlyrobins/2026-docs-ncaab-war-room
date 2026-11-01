const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ids=['date','health','status','games','ratingsPaste','ratingsDate','ratingsSeason','previewImport','saveImport','clearImport','importStatus','importPreview','localEfficiency','localTempo','manual','an','hn','ao','ad','at','ho','hd','ht','ne','nt','result','load'];
const elements=Object.fromEntries(ids.map(id=>[id,{value:'',textContent:'',innerHTML:'',disabled:false}]));
for(const [id,value] of Object.entries({an:'Notre Dame',hn:'Villanova',ao:110.6,ad:99.8,at:69.8,ho:119,hd:98.3,ht:70.4,ne:106,nt:71.5,localEfficiency:106,localTempo:71.5}))elements[id].value=String(value);
elements.manual.requestSubmit=()=>elements.manual.onsubmit({preventDefault(){}});
const storage=new Map(),event={date:'2026-11-01T14:30Z',competitions:[{neutralSite:true,competitors:[{homeAway:'away',team:{id:'87',displayName:'Notre Dame Fighting Irish',shortDisplayName:'Notre Dame'}},{homeAway:'home',team:{id:'222',displayName:'Villanova Wildcats',shortDisplayName:'Villanova'}}]}]};
const context=vm.createContext({console,Intl,Date,Number,JSON,String,Array,Error,AbortSignal,document:{getElementById:id=>elements[id],querySelectorAll:()=>[]},RatingsImport:require('../calculator/import.js'),localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},fetch:async url=>{assert.ok(!String(url).includes('110.6'));return String(url).startsWith('https://')?{ok:true,json:async()=>({events:[event]})}:{ok:false};}});
vm.runInContext(fs.readFileSync('calculator/calculator.js','utf8'),context);
(async()=>{
 elements.ratingsPaste.value='Team\tAdjOE\tAdjDE\tAdjT\nNotre Dame\t110.6\t99.8\t69.8\nVillanova\t119\t98.3\t70.4';
 elements.previewImport.onclick();assert.equal(elements.saveImport.disabled,false);
 elements.ratingsDate.value='2026-11-01';elements.ratingsSeason.value='2027';elements.date.value='2026-11-01';elements.saveImport.onclick();await new Promise(setImmediate);
 assert.match(elements.status.textContent,/1\/1/);assert.match(elements.games.innerHTML,/148.2/);assert.equal(elements.ratingsPaste.value,'');assert.equal(storage.size,1);
 elements.date.value='2025-11-01';await elements.load.onclick();assert.match(elements.status.textContent,/selected schedule is season 2026/);
 elements.date.value='2026-10-31';await elements.load.onclick();assert.match(elements.status.textContent,/after the selected game date/);
 elements.clearImport.onclick();assert.equal(storage.size,0);
 console.log('Browser flow checks passed: preview, save, slate calculation, season/date guards, clear.');
})().catch(e=>{console.error(e);process.exitCode=1;});
