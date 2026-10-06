function renderHome(){
  show('homeScreen');
  $('#homeScreen').innerHTML='<div class="home-wrap"><div class="home-top">'+brand()+'<button class="icon-button" id="homeSettings" aria-label="Settings">•••</button></div><div class="home-hero"><h1>One library.<br>Every game.</h1><p>Offline kits, rankings, teams, equipment and roster planning with every source kept auditable.</p></div><div class="section-label">Library</div><div class="game-library" id="gameLibrary"></div></div>';
  const grid=$('#gameLibrary');
  for(const g of catalog.games||[]){
    const btn=document.createElement('button');btn.className='game-tile';
    const icon=g.icon_path?'<img src="'+esc(g.icon_path)+'" alt="">':'<img class="brand-logo" src="brand-mark.svg" alt="">';
    const count=Number(g.character_count||0)||catalog.entities.filter(e=>e.game_id===g.id).length;
    btn.innerHTML='<div class="game-tile-art">'+icon+'</div><span class="game-tile-name">'+esc(g.name)+'</span><span class="game-tile-meta">'+count+' characters • offline</span>';
    btn.onclick=()=>location.hash='game/'+g.id+'/characters';grid.appendChild(btn)
  }
  $('#homeSettings').onclick=renderSettings;
}
function sectionLabel(s){return ({characters:'Characters',rankings:'Rankings',teams:'Teams',equipment:'Equipment',roster:'Roster'})[s]||s}
function renderGame(){
  show('gameScreen');const g=gameById(state.gameId);if(!g){location.hash='';return}
  const icon=g.icon_path?'<img class="game-mini-icon" src="'+esc(g.icon_path)+'" alt="">':'<img class="game-mini-icon" src="brand-mark.svg" alt="">';
  $('#gameScreen').innerHTML='<div class="game-shell"><header class="game-appbar"><div class="game-appbar-row"><button class="icon-button" id="gameBack" aria-label="Back">‹</button><div class="game-title-block">'+icon+'<div><div class="game-title">'+esc(g.name)+'</div><div class="game-subtitle">Local Codex</div></div></div><button class="icon-button" id="gameSettings" aria-label="Settings">•••</button></div><nav class="tabs" id="gameTabs">'+['characters','rankings','teams','equipment','roster'].map(s=>'<button class="tab '+(state.section===s?'active':'')+'" data-section="'+s+'">'+sectionLabel(s)+'</button>').join('')+'</nav></header><main class="browser-body" id="browserBody"></main></div>';
  $('#gameBack').onclick=()=>location.hash='';
  $('#gameSettings').onclick=renderSettings;
  $('#gameTabs').querySelectorAll('.tab').forEach(b=>b.onclick=()=>{state.section=b.dataset.section;state.query='';location.hash='game/'+state.gameId+'/'+state.section});
  renderGameSection();
}
function searchBar(placeholder,showFilter=false){
  return '<div class="search-row"><label class="search-box"><span>⌕</span><input id="browserSearch" type="search" placeholder="'+esc(placeholder)+'" value="'+esc(state.query)+'"></label>'+(showFilter?'<button class="filter-button" id="filterButton">Filters</button>':'')+'</div>';
}
function renderGameSection(){
  const body=$('#browserBody');if(!body)return;
  if(state.section==='characters')renderCharacters(body,false);
  else if(state.section==='roster')renderRoster(body);
  else if(state.section==='equipment')renderEquipment(body);
  else if(state.section==='rankings')renderRankings(body);
  else if(state.section==='teams')renderTeams(body);
}
function renderCharacters(body,ownedOnly){
  body.innerHTML=searchBar(ownedOnly?'Search owned characters…':'Search characters…',true)+'<div class="count-row"><span class="result-count" id="resultCount"></span><span class="active-filter-summary" id="filterSummary"></span></div><div id="browserGrid"></div>';
  $('#browserSearch').addEventListener('input',e=>{state.query=e.target.value;renderCharacterGrid(ownedOnly)});
  $('#filterButton').onclick=renderFilters;renderCharacterGrid(ownedOnly);
}
function renderCharacterGrid(ownedOnly=false){
  const grid=$('#browserGrid');if(!grid)return;const rows=characterRows(ownedOnly);
  $('#resultCount').textContent=rows.length+(ownedOnly?' owned':' characters');
  const filterCount=['rarity','faction','attribute','profession'].filter(k=>state.filters[k]).length;
  $('#filterSummary').textContent=filterCount?filterCount+' filter'+(filterCount>1?'s':'')+' active':'';
  grid.className='character-grid';grid.innerHTML='';
  if(!rows.length){grid.innerHTML='<div class="empty-state"><strong>'+(ownedOnly?'Your roster is empty':'No characters found')+'</strong>'+(ownedOnly?'Open any character and tap “Add to roster”.':'Try changing the search or filters.')+'</div>';return}
  const tpl=$('#characterCardTemplate');
  for(const e of rows){
    const n=tpl.content.cloneNode(true),btn=n.querySelector('.character-card'),img=chooseImage(e,'grid_card',['card','portrait','icon']),im=n.querySelector('.character-art');if(img)im.src=assetSrc(img);
    n.querySelector('.rarity-badge').textContent=e.rarity_key||'';
    n.querySelector('.character-name').textContent=displayName(e);
    const prof=entityRoles(e).map(professionLabel).join(' / ');
    n.querySelector('.character-meta').textContent=[e.attribute_type,factionLabel(e.faction_key),prof].filter(Boolean).join(' • ');
    if(isOwned(e.id)){const owned=document.createElement('span');owned.className='owned-badge';owned.textContent='OWNED';n.querySelector('.character-art-wrap').appendChild(owned)}
    btn.onclick=()=>location.hash='character/'+e.id;grid.appendChild(n)
  }
}
function accountCoverageGain(candidate,owned,mode){
  const ca=scenarioAxes(candidate,mode),base={};
  for(const k of axisOrder)base[k]=owned.length?Math.max(...owned.map(e=>Number(scenarioAxes(e,mode)[k]?.score||0))):0;
  let gain=0;for(const k of ['offense','tempo','survivability','control','support','disruption'])gain+=Math.max(0,Number(ca[k]?.score||0)-base[k]);
  return gain/6;
}
function accountCoverageRows(mode){
  const owned=activeGameEntities().filter(e=>isOwned(e.id)),unowned=activeGameEntities().filter(e=>!isOwned(e.id)&&scenario(e,mode));
  return unowned.map(e=>({entity:e,value:accountCoverageGain(e,owned,mode),kind:'coverage'})).sort((a,b)=>b.value-a.value||Number(scenario(b.entity,mode)?.score||0)-Number(scenario(a.entity,mode)?.score||0)).slice(0,20);
}
function accountWorkerPayload(mode){
  const owned=ownedIds(),ctx=teamModeContext(mode),candidates=[...ctx.byId.values()];
  const edges=[];
  for(const [key,strength] of ctx.edges.entries()){
    const [a,b]=key.split(':').map(Number);
    if(owned.has(a)||owned.has(b))edges.push({a,b,strength});
  }
  return {
    op:'account',mode,ownedIds:[...owned],
    teamSize:Number(catalog.team_optimizer?.team_size||catalog.adapter?.team_size||6),
    beamWidth:Math.min(Number(catalog.team_optimizer?.beam_width||120),96),
    candidates:candidates.map(m=>({id:m.entity.id,score:m.score,axes:axisOrder.map(k=>Number(m.axes[k]?.score||0)),norm:m.norm})),
    fixedIds:[],coverageAxes:(ctx.coverageAxes||[]).map(k=>axisOrder.indexOf(k)).filter(i=>i>=0),
    synergyBonusCap:Number(catalog.adapter?.team_optimizer?.synergy_bonus_cap||15),
    coverageBonusCap:Number(catalog.adapter?.team_optimizer?.coverage_bonus_cap||12),
    redundancyPenaltyCap:Number(catalog.adapter?.team_optimizer?.duplicate_profile_penalty_cap||8),
    edges
  };
}
function runAccountWorker(payload,onProgress){
  return new Promise((resolve,reject)=>{
    let worker;try{worker=new Worker('optimizer_worker.js')}catch(err){reject(err);return}
    let settled=false;
    worker.onmessage=e=>{const msg=e.data||{};if(msg.type==='progress'){onProgress?.(msg);return}if(msg.type==='account_result'){settled=true;worker.terminate();resolve(msg.values||[]);return}if(msg.type==='error'){settled=true;worker.terminate();reject(new Error(msg.message||'Roster analysis failed'))}};
    worker.onerror=e=>{if(!settled){settled=true;worker.terminate();reject(new Error(e.message||'Roster worker failed'))}};
    worker.postMessage(payload);
  });
}
async function renderAccountValue(){
  const host=$('#accountValueList');if(!host)return;
  const owned=activeGameEntities().filter(e=>isOwned(e.id)),teamSize=Number(catalog.adapter?.team_size||6);
  let rows=[];
  if(owned.length<teamSize){
    rows=accountCoverageRows(state.accountMode);
  }else{
    host.innerHTML='<div class="optimizer-progress"><span class="spinner"></span><div><strong>Analyzing your roster</strong><small id="accountStatus">Building your best owned team…</small></div></div>';
    try{
      const values=await runAccountWorker(accountWorkerPayload(state.accountMode),msg=>{const s=$('#accountStatus');if(s)s.textContent=msg.label||'Comparing additions…'});
      rows=values.map(x=>({entity:entityById(x.id),value:Number(x.value||0),baseline:x.baseline,team:x.bestTeam,kind:'team_gain'})).filter(x=>x.entity);
    }catch(err){
      rows=accountCoverageRows(state.accountMode);
    }
  }
  if(!$('#accountValueList'))return;
  if(!rows.length){host.innerHTML='<div class="empty-state"><strong>No recommendations</strong>Your roster already contains every character.</div>';return}
  host.innerHTML=rows.map((r,i)=>{const e=r.entity,img=chooseImage(e,'grid_card',['card']),sc=scenario(e,state.accountMode),value=r.kind==='team_gain'?(r.value.toFixed(1)+' team gain'):(r.value.toFixed(1)+' coverage gain');return '<button class="account-value-row" data-id="'+e.id+'><span class="rank-number">#'+(i+1)+'</span>'+(img?'<img src="'+esc(assetSrc(img))+'" alt="">':'')+'<div><strong>'+esc(displayName(e))+'</strong><span>'+esc(sc?.grade||'')+' • '+Math.round(Number(sc?.score||0))+' scenario index</span><small>'+esc(value)+'</small></div></button>'}).join('');
  host.querySelectorAll('.account-value-row').forEach(b=>b.onclick=()=>location.hash='character/'+b.dataset.id);
}
function renderRoster(body){
  const owned=activeGameEntities().filter(e=>isOwned(e.id));if(!rankingModes()[state.accountMode])state.accountMode=Object.keys(rankingModes())[0]||'general_pve';
  body.innerHTML='<section class="roster-summary"><div><span class="eyebrow">Personal roster</span><h2>'+owned.length+' owned characters</h2><p>Owned state stays local on this device. Account value measures what an unowned character adds to your current roster under the selected resource/scenario assumption.</p></div></section><section class="panel-section roster-value"><div class="section-head"><div><span class="eyebrow">Account-specific value</span><h2>Best next additions</h2></div><label class="mode-select"><span>Scenario</span><select id="accountMode">'+modeOptions(state.accountMode)+'</select></label></div><p class="muted small">'+(owned.length>=(catalog.adapter?.team_size||6)?'Ranked by improvement to your best roster-constrained team.':'Roster has fewer than '+(catalog.adapter?.team_size||6)+' members, so additions are ranked by missing axis coverage until a full team can be formed.')+'</p><div id="accountValueList" class="account-value-list"></div></section><div id="rosterGridHost"></div>';
  $('#accountMode').onchange=e=>{state.accountMode=e.target.value;renderAccountValue()};renderAccountValue();
  const host=$('#rosterGridHost');host.innerHTML='<div class="search-row"><label class="search-box"><span>⌕</span><input id="browserSearch" type="search" placeholder="Search owned characters…" value="'+esc(state.query)+'"></label><button class="filter-button" id="filterButton">Filters</button></div><div class="count-row"><span class="result-count" id="resultCount"></span><span class="active-filter-summary" id="filterSummary"></span></div><div id="browserGrid"></div>';
  $('#browserSearch').addEventListener('input',e=>{state.query=e.target.value;renderCharacterGrid(true)});$('#filterButton').onclick=renderFilters;renderCharacterGrid(true);
}

function renderEquipment(body){
  const types=subsystemTypes();if(!types.some(x=>x.key===state.equipmentKind)&&types.length)state.equipmentKind=types[0].key;body.innerHTML='<div class="segment-row">'+types.map(x=>'<button class="segment '+(state.equipmentKind===x.key?'active':'')+'" data-kind="'+esc(x.key)+'">'+esc(x.label)+'</button>').join('')+'</div>'+searchBar('Search equipment…',false)+'<div class="count-row"><span class="result-count" id="resultCount"></span></div><div id="browserGrid"></div>';
  body.querySelectorAll('.segment').forEach(b=>b.onclick=()=>{state.equipmentKind=b.dataset.kind;state.query='';renderEquipment(body)});
  $('#browserSearch').addEventListener('input',e=>{state.query=e.target.value;renderEquipmentGrid()});renderEquipmentGrid();
}
function renderEquipmentGrid(){
  const rows=subsystemRows(),grid=$('#browserGrid');const t=subsystemTypes().find(x=>x.key===state.equipmentKind);$('#resultCount').textContent=rows.length+' '+String(t?.label||state.equipmentKind).toLowerCase();
  grid.className='subsystem-grid';grid.innerHTML='';if(!rows.length){grid.innerHTML='<div class="empty-state"><strong>No records found</strong>Try a different search.</div>';return}
  const tpl=$('#subsystemCardTemplate');for(const s of rows){const n=tpl.content.cloneNode(true),btn=n.querySelector('.subsystem-card'),img=chooseImage(s,'grid_card',['card','icon']);if(img)n.querySelector('.subsystem-art').src=assetSrc(img);n.querySelector('.subsystem-name').textContent=s.name;n.querySelector('.subsystem-meta').textContent=s.subsystem_type==='soul'?(s.profession_fit||[]).map(professionLabel).join(' / ')||'Soul':s.subsystem_type.replace('_',' ');btn.onclick=()=>location.hash='subsystem/'+s.subsystem_type+'/'+encodeURIComponent(s.subsystem_key);grid.appendChild(n)}
}
function modeOptions(current){return Object.entries(rankingModes()).map(([k,v])=>'<option value="'+esc(k)+'" '+(k===current?'selected':'')+'>'+esc(v.label||k)+'</option>').join('')}
function renderRankings(body){
  if(!rankingModes()[state.rankingMode])state.rankingMode=Object.keys(rankingModes())[0]||'general_pve';
  body.innerHTML='<section class="ranking-head"><div><span class="eyebrow">Codex evaluation</span><h2>Character rankings</h2><p>Scenario-specific Codex results from normalized sourced mechanics. Source/community tiers never enter the score.</p></div><label class="mode-select"><span>Scenario</span><select id="rankingMode">'+modeOptions(state.rankingMode)+'</select></label></section><div id="rankingList" class="ranking-list"></div>';
  $('#rankingMode').onchange=e=>{state.rankingMode=e.target.value;renderRankings(body)};
  const r=rankingFor(state.rankingMode),list=$('#rankingList');if(!r){list.innerHTML='<div class="empty-state"><strong>No ranking data</strong>This adapter has no evaluation for that scenario.</div>';return}
  list.innerHTML=(r.entries||[]).map(row=>{const e=entityById(row.entity_id),img=chooseImage(e,'grid_card',['card','portrait','icon']),axes=scenarioAxes(e,state.rankingMode),top=axisOrder.map(k=>({k,v:Number(axes[k]?.score||0)})).sort((a,b)=>b.v-a.v).slice(0,3);return '<button class="ranking-row" data-id="'+e.id+'"><div class="rank-number">#'+row.rank+'</div>'+(img?'<img src="'+esc(assetSrc(img))+'" alt="">':'<div class="rank-art-empty"></div>')+'<div class="rank-main"><strong>'+esc(displayName(e))+'</strong><span>'+esc(confidenceLabel(row.confidence))+'</span><div class="mini-axis-row">'+top.map(x=>'<i><b style="width:'+Math.round(x.v)+'%"></b><em>'+esc(axisLabel(x.k))+'</em></i>').join('')+'</div></div><div class="rank-grade '+gradeClass(row.grade)+'"><strong>'+esc(row.grade)+'</strong><span>'+Math.round(row.score)+'</span></div></button>'}).join('');
  list.querySelectorAll('.ranking-row').forEach(b=>b.onclick=()=>location.hash='character/'+b.dataset.id);
}
let _teamEdgeCache=null;
let _teamModeCache=new Map();
function edgeMap(){
  if(_teamEdgeCache)return _teamEdgeCache;
  const m=new Map();
  for(const x of catalog.team_optimizer?.synergy_edges||[]){
    const key=Math.min(x.a,x.b)+':'+Math.max(x.a,x.b);
    m.set(key,Math.max(Number(x.strength||0),m.get(key)||0));
  }
  _teamEdgeCache=m;return m;
}
function teamModeContext(mode){
  const cacheKey=String(state.gameId)+':'+mode;
  if(_teamModeCache.has(cacheKey))return _teamModeCache.get(cacheKey);
  const byId=new Map();
  for(const e of activeGameEntities()){
    const sc=scenario(e,mode);if(!sc)continue;
    const axes=scenarioAxes(e,mode),vec=axisOrder.map(k=>Number(axes[k]?.score||0)),norm=Math.sqrt(vec.reduce((s,x)=>s+x*x,0))||1;
    byId.set(e.id,{entity:e,score:Number(sc.score||0),axes,vec,norm});
  }
  const ctx={byId,edges:edgeMap(),coverageAxes:catalog.team_optimizer?.coverage_axes||['offense','survivability','control','support','disruption','tempo']};
  _teamModeCache.set(cacheKey,ctx);return ctx;
}
function teamScore(ids,mode){
  const ctx=teamModeContext(mode),members=ids.map(id=>ctx.byId.get(id)).filter(Boolean),cfg=catalog.team_optimizer||{};
  if(!members.length)return {total:0,base:0,synergy:0,coverage:0,redundancy:0};
  const base=members.reduce((s,m)=>s+m.score,0)/members.length;
  let edgeRaw=0;
  for(let i=0;i<members.length;i++)for(let j=i+1;j<members.length;j++)edgeRaw+=ctx.edges.get(Math.min(members[i].entity.id,members[j].entity.id)+':'+Math.max(members[i].entity.id,members[j].entity.id))||0;
  const synergy=Math.min(Number(catalog.adapter?.team_optimizer?.synergy_bonus_cap||15),edgeRaw*1.6);
  let cov=0;
  for(const k of ctx.coverageAxes)cov+=Math.max(...members.map(m=>Number(m.axes[k]?.score||0)))/100;
  const coverage=Math.min(Number(catalog.adapter?.team_optimizer?.coverage_bonus_cap||12),(cov/ctx.coverageAxes.length)*12);
  let sim=0,pairs=0;
  for(let i=0;i<members.length;i++)for(let j=i+1;j<members.length;j++){
    let dot=0;for(let q=0;q<axisOrder.length;q++)dot+=members[i].vec[q]*members[j].vec[q];
    sim+=dot/(members[i].norm*members[j].norm);pairs++;
  }
  const avgSim=pairs?sim/pairs:0,redundancy=Math.max(0,(avgSim-.82)/.18)*Number(catalog.adapter?.team_optimizer?.duplicate_profile_penalty_cap||8);
  return {total:Math.min(100,Math.max(0,base*.78+synergy+coverage-redundancy)),base,synergy,coverage,redundancy};
}
function buildGreedyTeam(mode,fixed,candidates,teamSize,forbidden=new Set()){
  const team=[...fixed].filter(id=>!forbidden.has(id)),fixedSet=new Set(team);
  while(team.length<teamSize){
    let bestId=null,bestScore=-Infinity;
    for(const e of candidates){
      if(team.includes(e.id)||forbidden.has(e.id))continue;
      const score=teamScore([...team,e.id],mode).total;
      if(score>bestScore){bestScore=score;bestId=e.id}
    }
    if(bestId==null)break;team.push(bestId);
  }
  if(team.length!==teamSize)return null;
  for(let pass=0;pass<2;pass++){
    let changed=false;
    for(let i=0;i<team.length;i++){
      if(fixedSet.has(team[i]))continue;
      let bestId=team[i],bestScore=teamScore(team,mode).total;
      for(const e of candidates){
        if(team.includes(e.id)||forbidden.has(e.id))continue;
        const trial=team.slice();trial[i]=e.id;const score=teamScore(trial,mode).total;
        if(score>bestScore+0.001){bestScore=score;bestId=e.id}
      }
      if(bestId!==team[i]){team[i]=bestId;changed=true}
    }
    if(!changed)break;
  }
  return {ids:team,components:teamScore(team,mode)};
}
function optimizeTeam(mode,anchorId=null,excludeId=null,ownedOnly=false,fixedIds=[],allowedIds=null){
  const teamSize=Number(catalog.team_optimizer?.team_size||catalog.adapter?.team_size||6),owned=ownedIds();
  const fixed=[...new Set([...(fixedIds||[]),...(anchorId?[anchorId]:[])])].filter(id=>id!==excludeId);
  if(fixed.length>teamSize||ownedOnly&&fixed.some(id=>!owned.has(id)))return [];
  const allowed=allowedIds?new Set(allowedIds):null,ctx=teamModeContext(mode);
  let candidates=[...ctx.byId.values()].map(x=>x.entity).filter(e=>e.id!==excludeId&&(!allowed||allowed.has(e.id))&&(!ownedOnly||owned.has(e.id)));
  const edges=ctx.edges;
  candidates.sort((a,b)=>{
    const affinity=id=>fixed.reduce((s,f)=>s+(edges.get(Math.min(id,f)+':'+Math.max(id,f))||0),0);
    return (Number(scenario(b,mode)?.score||0)+affinity(b.id)*3)-(Number(scenario(a,mode)?.score||0)+affinity(a.id)*3);
  });
  const pool=Math.min(Number(catalog.team_optimizer?.candidate_pool||48),36);
  candidates=candidates.slice(0,pool);
  for(const id of fixed){if(!candidates.some(e=>e.id===id)){const a=entityById(id);if(a&&ctx.byId.has(id))candidates.unshift(a)}}
  const first=buildGreedyTeam(mode,fixed,candidates,teamSize,new Set(excludeId?[excludeId]:[]));if(!first)return [];
  const results=[first],seen=new Set([first.ids.slice().sort((a,b)=>a-b).join(',')]);
  for(const drop of first.ids.filter(id=>!fixed.includes(id)).slice(0,4)){
    const alt=buildGreedyTeam(mode,fixed,candidates,teamSize,new Set([...(excludeId?[excludeId]:[]),drop]));
    if(!alt)continue;const sig=alt.ids.slice().sort((a,b)=>a-b).join(',');
    if(!seen.has(sig)){seen.add(sig);results.push(alt)}
  }
  return results.sort((a,b)=>b.components.total-a.components.total).slice(0,4);
}
function fixedTeamChips(){
  if(!state.teamFixed.length)return '<span class="muted small">No locked members.</span>';
  return state.teamFixed.map(id=>{const e=entityById(id);return '<button class="locked-chip" data-remove-fixed="'+id+'>'+esc(displayName(e))+' ×</button>'}).join('');
}
function optimizerPayload(mode,anchorId,excludeId,ownedOnly,fixedIds=[]){
  const owned=ownedIds(),ctx=teamModeContext(mode),fixed=[...new Set([...(fixedIds||[]),...(anchorId?[anchorId]:[])])].filter(id=>id!==excludeId);
  let candidates=[...ctx.byId.values()].filter(m=>m.entity.id!==excludeId&&(!ownedOnly||owned.has(m.entity.id)));
  candidates.sort((a,b)=>b.score-a.score);
  const pool=Math.min(Number(catalog.team_optimizer?.candidate_pool||48),48);
  candidates=candidates.slice(0,pool);
  for(const id of fixed){
    if(!candidates.some(x=>x.entity.id===id)){
      const m=ctx.byId.get(id);if(m)candidates.unshift(m);
    }
  }
  const candidateIds=new Set(candidates.map(x=>x.entity.id));
  const edges=[];
  for(const [key,strength] of ctx.edges.entries()){
    const [a,b]=key.split(':').map(Number);
    if(candidateIds.has(a)&&candidateIds.has(b))edges.push({a,b,strength});
  }
  return {
    op:'optimize',
    mode,
    teamSize:Number(catalog.team_optimizer?.team_size||catalog.adapter?.team_size||6),
    beamWidth:Math.min(Number(catalog.team_optimizer?.beam_width||120),96),
    candidates:candidates.map(m=>({id:m.entity.id,score:m.score,axes:axisOrder.map(k=>Number(m.axes[k]?.score||0)),norm:m.norm})),
    fixedIds:fixed,
    excludeId:excludeId||null,
    coverageAxes:(ctx.coverageAxes||[]).map(k=>axisOrder.indexOf(k)).filter(i=>i>=0),
    synergyBonusCap:Number(catalog.adapter?.team_optimizer?.synergy_bonus_cap||15),
    coverageBonusCap:Number(catalog.adapter?.team_optimizer?.coverage_bonus_cap||12),
    redundancyPenaltyCap:Number(catalog.adapter?.team_optimizer?.duplicate_profile_penalty_cap||8),
    edges
  };
}
function runOptimizerWorker(payload,onProgress){
  return new Promise((resolve,reject)=>{
    let worker;
    try{worker=new Worker('optimizer_worker.js')}catch(err){reject(err);return}
    let settled=false;
    worker.onmessage=e=>{
      const msg=e.data||{};
      if(msg.type==='progress'){onProgress?.(msg);return}
      if(msg.type==='result'){settled=true;worker.terminate();resolve(msg.teams||[]);return}
      if(msg.type==='error'){settled=true;worker.terminate();reject(new Error(msg.message||'Optimizer failed'))}
    };
    worker.onerror=e=>{if(!settled){settled=true;worker.terminate();reject(new Error(e.message||'Optimizer worker failed'))}};
    worker.postMessage(payload);
  });
}
function renderTeams(body){
  if(!rankingModes()[state.teamMode])state.teamMode=Object.keys(rankingModes())[0]||'general_pve';
  const chars=activeGameEntities().slice().sort((a,b)=>displayName(a).localeCompare(displayName(b))),opts='<option value="">None</option>'+chars.map(e=>'<option value="'+e.id+'">'+esc(displayName(e))+'</option>').join('');
  body.innerHTML='<section class="ranking-head"><div><span class="eyebrow">Team optimizer</span><h2>Build a team</h2><p>Optimize from sourced Codex mechanics. Lock existing teammates to answer “replace Y”, build around a unit, exclude a unit, or constrain the search to your roster.</p></div></section><div class="team-controls"><label><span>Scenario</span><select id="teamMode">'+modeOptions(state.teamMode)+'</select></label><label><span>Build around</span><select id="teamAnchor">'+opts+'</select></label><label><span>Exclude / replace</span><select id="teamExclude">'+opts+'</select></label><label class="check-row"><input id="teamOwnedOnly" type="checkbox" '+(state.teamOwnedOnly?'checked':'')+'><span>Use owned roster only</span></label><label class="team-lock-select"><span>Lock teammate</span><select id="teamFixedAdd">'+opts+'</select></label><button class="secondary-button" id="addFixed">Lock member</button><div class="locked-members" id="lockedMembers">'+fixedTeamChips()+'</div><button class="primary-button" id="runTeam">Optimize team</button></div><div id="teamResults"></div>';
  $('#teamMode').value=state.teamMode;$('#teamAnchor').value=state.teamAnchor||'';$('#teamExclude').value=state.teamExclude||'';
  $('#teamMode').onchange=e=>state.teamMode=e.target.value;
  $('#teamAnchor').onchange=e=>state.teamAnchor=e.target.value?Number(e.target.value):null;
  $('#teamExclude').onchange=e=>state.teamExclude=e.target.value?Number(e.target.value):null;
  $('#teamOwnedOnly').onchange=e=>state.teamOwnedOnly=e.target.checked;
  $('#addFixed').onclick=()=>{const id=Number($('#teamFixedAdd').value||0);if(id&&!state.teamFixed.includes(id)&&state.teamFixed.length<(catalog.adapter?.team_size||6)){state.teamFixed.push(id);renderTeams(body)}};
  body.querySelectorAll('[data-remove-fixed]').forEach(b=>b.onclick=()=>{state.teamFixed=state.teamFixed.filter(x=>x!==Number(b.dataset.removeFixed));renderTeams(body)});
  $('#runTeam').onclick=()=>{if(!state.teamBusy)renderTeamResults()};
}
async function renderTeamResults(){
  const host=$('#teamResults'),teamSize=Number(catalog.adapter?.team_size||6),button=$('#runTeam');
  if(state.teamOwnedOnly&&ownedIds().size<teamSize){host.innerHTML='<div class="empty-state"><strong>Not enough owned characters</strong>Add at least '+teamSize+' characters to your roster.</div>';return}
  const fixed=[...new Set([...(state.teamFixed||[]),...(state.teamAnchor?[state.teamAnchor]:[])])].filter(id=>id!==state.teamExclude);
  if(fixed.length>teamSize){host.innerHTML='<div class="empty-state"><strong>Too many locked characters</strong>Remove a locked member and try again.</div>';return}
  state.teamBusy=true;if(button){button.disabled=true;button.textContent='Optimizing…'}
  host.innerHTML='<div class="optimizer-progress"><span class="spinner"></span><div><strong>Building teams</strong><small id="optimizerStatus">Preparing candidates…</small></div></div>';
  try{
    const payload=optimizerPayload(state.teamMode,state.teamAnchor,state.teamExclude,state.teamOwnedOnly,state.teamFixed);
    let teams;
    try{
      teams=await runOptimizerWorker(payload,msg=>{const s=$('#optimizerStatus');if(s)s.textContent=msg.label||('Evaluating '+(msg.depth||1)+'/'+payload.teamSize+' team slots…')});
    }catch(err){
      // Last-resort compatibility path for WebViews without Worker support.
      const s=$('#optimizerStatus');if(s)s.textContent='Using compatibility fallback…';
      await new Promise(resolve=>setTimeout(resolve,24));
      const oldPool=catalog.team_optimizer?.candidate_pool;
      if(catalog.team_optimizer)catalog.team_optimizer.candidate_pool=Math.min(Number(oldPool||24),20);
      teams=optimizeTeam(state.teamMode,state.teamAnchor,state.teamExclude,state.teamOwnedOnly,state.teamFixed);
      if(catalog.team_optimizer)catalog.team_optimizer.candidate_pool=oldPool;
    }
    if(!teams.length){host.innerHTML='<div class="empty-state"><strong>No valid team</strong>Change the constraints and try again.</div>';return}
    host.innerHTML=teams.map((t,idx)=>'<section class="team-result"><div class="team-result-head"><div><span class="eyebrow">'+(idx===0?'Best match':'Alternative '+idx)+'</span><h3>'+Math.round(t.components.total)+' team fit</h3></div><div class="team-components"><span>Base '+Math.round(t.components.base)+'</span><span>Synergy +'+Number(t.components.synergy||0).toFixed(1)+'</span><span>Coverage +'+Number(t.components.coverage||0).toFixed(1)+'</span>'+(t.components.redundancy?'<span>Overlap −'+Number(t.components.redundancy).toFixed(1)+'</span>':'')+'</div></div><div class="team-cards">'+t.ids.map(id=>{const e=entityById(id),img=chooseImage(e,'grid_card',['card']);return '<button class="team-member" data-id="'+id+'>'+(img?'<img src="'+esc(assetSrc(img))+'" alt="">':'')+'<strong>'+esc(displayName(e))+'</strong><span>'+esc(scenario(e,state.teamMode)?.grade||'')+'</span></button>'}).join('')+'</div></section>').join('');
    host.querySelectorAll('.team-member').forEach(b=>b.onclick=()=>location.hash='character/'+b.dataset.id);
  }finally{
    state.teamBusy=false;const live=$('#runTeam');if(live){live.disabled=false;live.textContent='Optimize team'}
  }
}

function renderFilters(){const rows=activeGameEntities(),vals=k=>[...new Set(rows.map(e=>e[k]).filter(Boolean))].sort(),professions=[...new Set(rows.flatMap(e=>entityRoles(e)))].sort(),options=(arr,current,fmt=x=>x)=>'<option value="">All</option>'+arr.map(v=>'<option value="'+esc(v)+'" '+(current===v?'selected':'')+'>'+esc(fmt(v))+'</option>').join('');$('#filterSheet').innerHTML='<div class="sheet-handle"></div><div class="sheet-head"><h2>Character filters</h2><button class="icon-button" id="closeFilter">×</button></div><div class="sheet-grid"><div class="sheet-field"><label>Rarity</label><select id="fRarity">'+options(vals('rarity_key'),state.filters.rarity)+'</select></div><div class="sheet-field"><label>Faction</label><select id="fFaction">'+options(vals('faction_key'),state.filters.faction,factionLabel)+'</select></div><div class="sheet-field"><label>Attribute</label><select id="fAttribute">'+options(vals('attribute_type'),state.filters.attribute)+'</select></div><div class="sheet-field"><label>Role</label><select id="fProfession">'+options(professions,state.filters.profession,professionLabel)+'</select></div><div class="sheet-field"><label>Sort</label><select id="fSort"><option value="name" '+(state.filters.sort==='name'?'selected':'')+'>Name</option><option value="release" '+(state.filters.sort==='release'?'selected':'')+'>Newest</option><option value="rarity" '+(state.filters.sort==='rarity'?'selected':'')+'>Rarity</option></select></div></div><div class="sheet-actions"><button class="secondary-button" id="clearFilters">Clear</button><button class="primary-button" id="applyFilters">Apply</button></div>';openSheet('filterSheet');$('#closeFilter').onclick=closeSheets;$('#clearFilters').onclick=()=>{state.filters={rarity:'',faction:'',attribute:'',profession:'',sort:'name'};closeSheets();renderGameSection()};$('#applyFilters').onclick=()=>{state.filters.rarity=$('#fRarity').value;state.filters.faction=$('#fFaction').value;state.filters.attribute=$('#fAttribute').value;state.filters.profession=$('#fProfession').value;state.filters.sort=$('#fSort').value;closeSheets();renderGameSection()}}
function renderSettings(){$('#settingsSheet').innerHTML='<div class="sheet-handle"></div><div class="sheet-head"><h2>Game Codex</h2><button class="icon-button" id="closeSettings">×</button></div><div class="settings-actions"><button id="importPack">Import database pack</button><button id="reloadApp">Reload app</button><button id="restorePack">Restore bundled database</button><button id="appInfo">Android app information</button></div><div class="settings-meta">Engine '+esc(catalog.engine_version||'unknown')+' • Adapter '+esc(catalog.adapter?.version||'—')+'<br>Personal roster data is stored locally on this device. Source provenance stays available from the character menu.</div>';openSheet('settingsSheet');$('#closeSettings').onclick=closeSheets;$('#importPack').onclick=()=>{closeSheets();nativeCall('choosePack')};$('#reloadApp').onclick=()=>{closeSheets();nativeCall('reload')};$('#restorePack').onclick=()=>{closeSheets();nativeCall('restoreBundledPack')};$('#appInfo').onclick=()=>{closeSheets();nativeCall('appInfo')}}
