'use strict';
// Run the real handlers against inert DOM/API objects; no Windows actions.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../TechLoungeTweaks/src/web/app.js'), 'utf8');
const start = source.indexOf('const INFLIGHT = {};');
const end = source.indexOf('async function rescan()', start);
assert(start >= 0 && end > start);
function element() {
  return {textContent:'', disabled:false, hidden:true, attributes:{},
    classList:{toggle(){}}, setAttribute(k,v){this.attributes[k]=v;},
    getAttribute(k){return k === 'role' ? 'switch' : this.attributes[k];}};
}
const tweaks = [
  {key:'first',name:'First tweak',category:'Privacy',applied:false},
  {key:'second',name:'Second tweak',category:'Privacy',applied:false},
  {key:'other',name:'Other tweak',category:'Graphics',applied:false}
];
const cards = new Map(tweaks.map(t => {
  const card = element(); card.sw=element(); card.badge=element();
  card.querySelector=s => s === '.sw' ? card.sw : card.badge;
  return [t.key,card];
}));
const status=element(); let request, finish;
const context={window:{},STATE:{tweaks,cats:['Privacy','Graphics'],page:'Privacy'},
  CSS:{escape:s=>s}, H:()=>status, RECOMMENDED_KEYS:['first','second'],
  confirmAction:async()=>true, banner:()=>{},
  document:{querySelector:selector=>cards.get(selector.match(/data-key="(.*?)"/)[1]),querySelectorAll:()=>[]},
  api:async(...args)=>{request=args;return await new Promise(resolve=>{finish=resolve;});}};
vm.createContext(context);
vm.runInContext(source.slice(start,end),context);
vm.runInContext('refreshCounts=()=>{};updateCounts=()=>{};',context);
(async()=>{
  const pending=vm.runInContext("applyCategory('Privacy',true)",context);
  await new Promise(setImmediate);
  assert.equal(request[0],'bulk'); const operation=request[3];
  assert.equal(cards.get('first').badge.textContent,'QUEUED');
  assert.equal(cards.get('other').sw.disabled,true);
  const emit=data=>context.window.py_tweak_progress({operation,total:2,...data});
  emit({key:'first',phase:'working',completed:0});
  assert.equal(cards.get('first').badge.textContent,'APPLYING…');
  assert.equal(tweaks[0].applied,false);
  tweaks[2].applied=true;
  vm.runInContext('reconcileTweaks({applied:{first:false}},[STATE.tweaks[0]])',context);
  assert.equal(tweaks[2].applied,true);
  emit({key:'first',phase:'verified',completed:1,applied:true});
  assert.equal(tweaks[0].applied,true);
  assert.equal(cards.get('first').sw.attributes['aria-checked'],'true');
  assert.equal(cards.get('second').badge.textContent,'QUEUED');
  emit({operation:operation+1,key:'first',phase:'verified',completed:1,applied:false});
  assert.equal(tweaks[0].applied,true);
  emit({key:'second',phase:'failed',completed:2,applied:false});
  assert.equal(cards.get('second').badge.textContent,'NEEDS ATTENTION');
  assert.match(status.textContent,/Second tweak.*2 of 2 checked/);
  finish({ok:false,applied:{first:true,second:false,other:false},errors:{second:'Blocked'}});
  await pending;
  assert.equal(cards.get('first').sw.disabled,false);
  assert.equal(cards.get('other').sw.disabled,false);
  assert.equal(cards.get('first').attributes['aria-busy'],'false');
  assert.equal(tweaks[1].applied,false);
  vm.runInContext("setToggle('first')",context);
  await new Promise(setImmediate);
  assert.equal(vm.runInContext('Object.keys(INFLIGHT).length',context),1);
  finish({ok:true,applied:false});
  await new Promise(setImmediate);
  assert.equal(vm.runInContext('Object.keys(INFLIGHT).length',context),0);
  assert.equal(tweaks[0].applied,false);
  console.log('PASS: real bulk UI updates a verified switch before batch completion, shows queued/failed states, ignores stale events and unlocks controls.');
  console.log('PASS: a finished individual toggle leaves no permanent in-flight key to block later scans.');
})().catch(error=>{console.error(error);process.exitCode=1;});
