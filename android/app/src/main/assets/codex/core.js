let catalog={games:[],entities:[],subsystems:[],compatibility:[],rankings:[],roster_accounts:[]};
const state={
  gameId:null,section:'characters',query:'',
  filters:{rarity:'',faction:'',attribute:'',profession:'',sort:'name'},
  equipmentKind:'soul',rankingMode:'general_pve',teamMode:'general_pve',
  teamAnchor:null,teamExclude:null,teamOwnedOnly:false,teamFixed:[],accountMode:'general_pve'
};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const parse=v=>{try{return typeof v==='string'?JSON.parse(v):v}catch{return {}}};
const badNames=/^(action failed|error|failed|undefined|null|unknown)$/i;
const mechanicLabels={
  damage:'Damage',physical_damage:'Physical damage',magic_damage:'Magic damage',true_damage:'True damage',piercing_damage:'Piercing damage',
  healing:'Healing',heal_block:'Healing block',shield:'Shield',damage_reduction:'Damage reduction',attack_up:'Attack up',attack_down:'Attack down',
  defense_up:'Defense up',defense_down:'Defense down',damage_up:'Damage up',damage_taken_up:'Damage vulnerability',revive:'Revive',
  death_prevention:'Death prevention',damage_immunity:'Damage immunity',buff:'Buff interaction',status_effect:'Status interaction',
  sakura_petals:'Sakura petals',sakura_release:'Sakura Release',crit_disable:'Critical suppression',defensive_immunity:'Defense bypass',
  extra_skill_cast:'Extra skill activation',guaranteed_hit:'Guaranteed hit',guaranteed_crit:'Guaranteed critical',defense_ignore:'Defense ignore',
  protection_ignore:'Protection ignore',penetration_up:'Penetration',status_resist_up:'Status resistance'
};
const axisOrder=['offense','tempo','survivability','control','support','disruption','reliability','independence','synergy_ceiling','counter_resilience'];
let familyBases={};
let roster={owned:{}};

function resetScroll(){window.scrollTo(0,0);document.documentElement.scrollLeft=0;document.body.scrollLeft=0;document.querySelectorAll('.tabs,.detail-nav,.segment-row').forEach(x=>x.scrollLeft=0)}
function show(id){for(const s of ['homeScreen','gameScreen','detailScreen'])$('#'+s).classList.toggle('hidden',s!==id)}
function assetSrc(img){if(!img)return '';const p=img.pack_path||img.local_path||'';return p.startsWith('assets/')?p:'assets/'+p.split(/[\\/]/).pop()}
function chooseImage(obj,role,types=[]){const imgs=(obj?.images||[]).filter(x=>x&&(x.pack_path||x.local_path)).sort((a,b)=>Number(b.priority||0)-Number(a.priority||0));return imgs.find(x=>x.display_role===role)||types.map(t=>imgs.find(x=>x.asset_type===t)).find(Boolean)||imgs[0]||null}
function keyFamily(e){return (e.entity_key||'').split(':').pop().replace(/^herocard_/,'').replace(/\d+$/,'')}
function isLatinName(s){return !!s&&/[A-Za-z]/.test(s)&&!/[\u3040-\u30ff\u3400-\u9fff]/.test(s)}
function buildFamilyBases(){const groups={};for(const e of catalog.entities||[])(groups[keyFamily(e)]??=[]).push(e);for(const [k,rows] of Object.entries(groups)){const candidates=rows.map(e=>e.display_name||e.canonical_name).filter(n=>isLatinName(n)&&!badNames.test(n)&&n.length<42&&!/[—·:&]/.test(n));if(candidates.length)familyBases[k]=candidates.sort((a,b)=>a.length-b.length)[0]}}
function displayName(e){if(!e)return 'Unknown';if(e.display_name&&!badNames.test(e.display_name))return e.display_name;const raw=e.canonical_name||'Unnamed',base=familyBases[keyFamily(e)];if(badNames.test(raw)&&base)return base;if(!isLatinName(raw)&&base)return base;return raw}
function gameById(id){return (catalog.games||[]).find(g=>Number(g.id)===Number(id))}
function entityById(id){return (catalog.entities||[]).find(e=>Number(e.id)===Number(id))}
function subsystemBy(type,key){return (catalog.subsystems||[]).find(s=>s.subsystem_type===type&&s.subsystem_key===key)}
function professionLabel(p){return ({attack:'Attack',assist:'Support',defend:'Defense',control:'Control'})[p]||p}
function entityRoles(e){const rows=e?.adapter_meta?.roles||e?.kaisen_meta?.professions||[];return [...new Set([...(Array.isArray(rows)?rows:[rows]),...(e?.role_key?[e.role_key]:[])].filter(Boolean))}
function subsystemTypes(){const types=catalog.adapter?.subsystems?.types||{};const configured=Object.entries(types).map(([key,cfg])=>({key,label:cfg.label||key,singular:cfg.singular||cfg.label||key}));if(configured.length)return configured;const keys=[...new Set((catalog.subsystems||[]).map(s=>s.subsystem_type).filter(Boolean))];return keys.map(key=>({key,label:key.replace(/_/g,' '),singular:key.replace(/_/g,' ')}))}
function humanMechanic(k){if(!k)return 'Mechanic interaction';if(mechanicLabels[k])return mechanicLabels[k];if(k.startsWith('status:'))return 'Unique status';return k.replace(/_/g,' ').replace(/\b\w/g,m=>m.toUpperCase())}
function effectsOfSkill(s){return (s.versions||[]).flatMap(v=>v.effects||[])}
function gameplaySkills(e){return (e.skills||[]).filter(s=>effectsOfSkill(s).length>0&&s.presentation_class!=='source_note'&&s.analysis_eligible!==false)}
function sourceNoteSkills(e){return (e.skills||[]).filter(s=>effectsOfSkill(s).length===0||s.presentation_class==='source_note'||s.analysis_eligible===false)}
function searchable(e){return [displayName(e),e.canonical_name,...(e.aliases||[]),...(e.skills||[]).flatMap(s=>[s.name,s.description_source])].join(' ').toLowerCase()}
function activeGameEntities(){return (catalog.entities||[]).filter(e=>Number(e.game_id)===Number(state.gameId))}
function evaluation(e){return e?.codex_evaluation||null}
function scenario(e,mode=state.rankingMode){return evaluation(e)?.scenarios?.[mode]||null}
function scenarioAxes(e,mode=state.rankingMode){const ev=evaluation(e),sc=ev?.scenarios?.[mode];if(!ev||!sc)return {};return sc.profile==='base'?ev.axes?.base||{}:sc.optimized_axes||ev.axes?.base||{}}
function rankingModes(){return catalog.adapter?.modes||{}}
function rankingFor(mode){return (catalog.rankings||[]).find(r=>r.mode_key===mode)}
function gradeClass(g){return 'grade-'+String(g||'').replace('+','plus').toLowerCase()}
function confidenceLabel(v){v=Number(v||0);return v>=.9?'High confidence':v>=.72?'Good confidence':v>=.5?'Moderate confidence':'Low confidence'}
function axisLabel(k){return catalog.adapter?.axes?.[k]?.label||k.replace(/_/g,' ').replace(/\b\w/g,m=>m.toUpperCase())}

function loadRoster(){
  try{const r=JSON.parse(localStorage.getItem('game_codex_roster_v1')||'{}');roster={owned:r.owned||{}}}catch{roster={owned:{}}}
}
function saveRoster(){localStorage.setItem('game_codex_roster_v1',JSON.stringify(roster))}
function isOwned(id){return !!roster.owned[String(id)]}
function setOwned(id,value){if(value)roster.owned[String(id)]={owned:true,updated_at:new Date().toISOString()};else delete roster.owned[String(id)];saveRoster()}
function ownedIds(){return new Set(Object.keys(roster.owned).map(Number))}

function characterRows(ownedOnly=false){
  let rows=activeGameEntities().filter(e=>{const q=state.query.trim().toLowerCase(),prof=e.kaisen_meta?.professions||[];return(!ownedOnly||isOwned(e.id))&&(!q||searchable(e).includes(q))&&(!state.filters.rarity||e.rarity_key===state.filters.rarity)&&(!state.filters.faction||e.faction_key===state.filters.faction)&&(!state.filters.attribute||e.attribute_type===state.filters.attribute)&&(!state.filters.profession||prof.includes(state.filters.profession))});
  rows.sort((a,b)=>state.filters.sort==='rarity'?String(b.rarity_key||'').localeCompare(String(a.rarity_key||''))||displayName(a).localeCompare(displayName(b)):state.filters.sort==='release'?String(b.kaisen_meta?.releaseDate||'').localeCompare(String(a.kaisen_meta?.releaseDate||''))||displayName(a).localeCompare(displayName(b)):displayName(a).localeCompare(displayName(b)));return rows
}
function activeSubsystems(){return (catalog.subsystems||[]).filter(s=>s.subsystem_type===state.equipmentKind)}
function subsystemRows(){const q=state.query.trim().toLowerCase();return activeSubsystems().filter(s=>!q||[s.name,s.subsystem_key,s.section,s.max_profile?.description].join(' ').toLowerCase().includes(q)).sort((a,b)=>String(a.name).localeCompare(String(b.name)))}

function closeSheets(){$('#sheetBackdrop').classList.add('hidden');$('#filterSheet').classList.add('hidden');$('#settingsSheet').classList.add('hidden');document.body.classList.remove('no-scroll')}
function openSheet(which){closeSheets();$('#sheetBackdrop').classList.remove('hidden');$('#'+which).classList.remove('hidden');document.body.classList.add('no-scroll')}
function nativeCall(name){try{if(window.AndroidCodex&&typeof AndroidCodex[name]==='function')AndroidCodex[name]()}catch(e){}}
function brand(){return '<div class="brand-row"><div class="brand-mark"></div><div><div class="brand-name">Game Codex</div><div class="brand-kicker">Offline intelligence library</div></div></div>'}
