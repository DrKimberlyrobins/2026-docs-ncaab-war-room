const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('app.js','utf8'),ctx={};vm.createContext(ctx);
vm.runInContext(src.slice(src.indexOf('const avg='),src.indexOf('const fmt='))+';this.baseline=baseline;',ctx);
let count=0;
for(const file of fs.readdirSync('data/daily').filter(f=>f.endsWith('.json'))){
 const p=JSON.parse(fs.readFileSync('data/daily/'+file)),slate=JSON.parse(fs.readFileSync('data/slates/'+file));
 assert.deepStrictEqual(p.matchups.map(x=>x.id).sort(),slate.data.events.map(x=>x.id).sort(),'Every source event retained for '+file);
 for(const row of p.matchups){
  if(!row.samples)continue;
  const expected=ctx.baseline(row.samples.away,row.samples.home);
  for(const key of ['full','half']){
   assert.equal(Boolean(row.model[key]),Boolean(expected[key]));
   if(expected[key])for(const field of ['away','home','total','homeMargin','nAway','nHome'])assert.ok(Math.abs(expected[key][field]-row.model[key][field])<1e-8);
  }
  count++;
 }
}
console.log('Prepared evidence verified: '+count+' matchup entries; every source event retained; Python/JavaScript baseline arithmetic agrees.');
