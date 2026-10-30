// No test framework needed: exercise the same core.js used by the Android WebView.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const storage=new Map();
const snapshots={};
const localStorage={
  getItem:k=>storage.get(k)||null,
  setItem:(k,v)=>storage.set(k,String(v))
};
const scope={localStorage,
  window:{AndroidCodex:{publishPilotSnapshot:s=>{const doc=JSON.parse(s);snapshots[doc.account]=doc}}},
  console,Date,Set,Map,Number,Object,Array,Math,JSON,
  route:()=>{},renderSettings:()=>{}
};
vm.createContext(scope);
const js=fs.readFileSync('android/app/src/main/assets/codex/core.js','utf8');
vm.runInContext(js,scope,{filename:'core.js'});
vm.runInContext(`catalog={engine_version:"0.8.0",
 entities:[
  {id:101,game_id:1,entity_key:"shoujo:101",display_name:"Hero A",
   rarity_key:"UR+",kaisen_meta:{professions:["attack"]},
   codex_evaluation:{scenarios:{general_pve:{score:72,confidence:.5}}}},
  {id:202,game_id:1,entity_key:"shoujo:202",display_name:"Hero B",
   rarity_key:"SSR",kaisen_meta:{professions:["defend"]}}]}`,scope);
storage.set('game_codex_roster_v1',JSON.stringify({owned:{101:{owned:true}}}));
vm.runInContext('loadRoster();publishPilotSummary()',scope);
assert.strictEqual(snapshots.unassigned.account,'unassigned');
assert.strictEqual(snapshots.unassigned.owned.length,1);
assert.strictEqual(snapshots.unassigned.owned[0].id,101);
assert.strictEqual(snapshots.unassigned.verified_game_inventory,false);
assert.strictEqual(snapshots.unassigned.grading_authorized,false);
vm.runInContext('setActiveCodexAccount("global");setOwned(202,true)',scope);
assert.strictEqual(snapshots.global.account,'global');
assert.deepStrictEqual(snapshots.global.owned.map(e=>e.id),[202]);
assert.deepStrictEqual(Object.keys(JSON.parse(storage.get('game_codex_roster_v1')).owned),['101']);
vm.runInContext('setActiveCodexAccount("jp");setOwned(101,true)',scope);
assert.deepStrictEqual(snapshots.jp.owned.map(e=>e.id),[101]);
assert.deepStrictEqual(snapshots.global.owned.map(e=>e.id),[202]);
assert.ok(snapshots.jp.generated_at>0);
assert.ok(snapshots.jp.catalog_engine);
assert.strictEqual('source_opinion' in snapshots.jp.owned[0],false);
console.log('PASS: legacy, global, JP snapshots isolated; unverified ownership preserved');
