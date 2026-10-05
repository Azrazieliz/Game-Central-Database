function renderHome(){
  show('homeScreen');
  $('#homeScreen').innerHTML='<div class="home-wrap"><div class="home-top">'+brand()+'<button class="icon-button" id="homeSettings" aria-label="Settings">•••</button></div><div class="home-hero"><h1>Your games.<br>One Codex.</h1><p>Offline character databases, rankings, teams, equipment and roster planning.</p></div><div class="section-label">Library</div><div class="game-library" id="gameLibrary"></div></div>';
  const grid=$('#gameLibrary');
  for(const g of catalog.games||[]){
    const btn=document.createElement('button');btn.className='game-tile';
    const icon=g.icon_path?'<img src="'+esc(g.icon_path)+'" alt="">':'<div class="brand-mark"></div>';
    const count=Number(g.character_count||0)||catalog.entities.filter(e=>e.game_id===g.id).length;
    btn.innerHTML='<div class="game-tile-art">'+icon+'</div><span class="game-tile-name">'+esc(g.name)+'</span><span class="game-tile-meta">'+count+' characters • offline</span>';
    btn.onclick=()=>location.hash='game/'+g.id+'/characters';grid.appendChild(btn)
  }
  $('#homeSettings').onclick=renderSettings;
}
function sectionLabel(s){return ({characters:'Characters',rankings:'Rankings',teams:'Teams',equipment:'Equipment',roster:'Roster'})[s]||s}
function renderGame(){
  show('gameScreen');const g=gameById(state.gameId);if(!g){location.hash='';return}
  const icon=g.icon_path?'<img class="game-mini-icon" src="'+esc(g.icon_path)+'" alt="">':'<div class="brand-mark"></div>';
  $('#gameScreen').innerHTML='<div class="game-shell"><header class="game-appbar"><div class="game-appbar-row"><button class="icon-button" id="gameBack" aria-label="Back">‹</button><div class="game-title-block">'+icon+'<div><div class="game-title">'+esc(g.name)+'</div><div class="game-subtitle">Game Codex</div></div></div><button class="icon-button" id="gameSettings" aria-label="Settings">•••</button></div><nav class="tabs" id="gameTabs">'+['characters','rankings','teams','equipment','roster'].map(s=>'<button class="tab '+(state.section===s?'active':'')+'" data-section="'+s+'">'+sectionLabel(s)+'</button>').join('')+'</nav></header><main class="browser-body" id="browserBody"></main></div>';
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
    const prof=(e.kaisen_meta?.professions||[]).map(professionLabel).join(' / ');
    n.querySelector('.character-meta').textContent=[e.attribute_type,e.faction_key,prof].filter(Boolean).join(' • ');
    if(isOwned(e.id)){const owned=document.createElement('span');owned.className='owned-badge';owned.textContent='OWNED';n.querySelector('.character-art-wrap').appendChild(owned)}
    btn.onclick=()=>location.hash='character/'+e.id;grid.appendChild(n)
  }
}
function renderRoster(body){
  const owned=activeGameEntities().filter(e=>isOwned(e.id));
  body.innerHTML='<section class="roster-summary"><div><span class="eyebrow">Personal roster</span><h2>'+owned.length+' owned characters</h2><p>Roster state stays local on this device and only affects account-specific planning.</p></div></section><div id="rosterGridHost"></div>';
  const host=$('#rosterGridHost');host.innerHTML='<div class="search-row"><label class="search-box"><span>⌕</span><input id="browserSearch" type="search" placeholder="Search owned characters…" value="'+esc(state.query)+'"></label><button class="filter-button" id="filterButton">Filters</button></div><div class="count-row"><span class="result-count" id="resultCount"></span><span class="active-filter-summary" id="filterSummary"></span></div><div id="browserGrid"></div>';
  $('#browserSearch').addEventListener('input',e=>{state.query=e.target.value;renderCharacterGrid(true)});$('#filterButton').onclick=renderFilters;renderCharacterGrid(true);
}
function renderEquipment(body){
  body.innerHTML='<div class="segment-row">'+[['soul','Souls'],['martial_spirit','Martial Spirits'],['mount','Mounts']].map(([k,l])=>'<button class="segment '+(state.equipmentKind===k?'active':'')+'" data-kind="'+k+'">'+l+'</button>').join('')+'</div>'+searchBar('Search equipment…',false)+'<div class="count-row"><span class="result-count" id="resultCount"></span></div><div id="browserGrid"></div>';
  body.querySelectorAll('.segment').forEach(b=>b.onclick=()=>{state.equipmentKind=b.dataset.kind;state.query='';renderEquipment(body)});
  $('#browserSearch').addEventListener('input',e=>{state.query=e.target.value;renderEquipmentGrid()});renderEquipmentGrid();
}
function renderEquipmentGrid(){
  const rows=subsystemRows(),grid=$('#browserGrid');$('#resultCount').textContent=rows.length+' '+({soul:'souls',martial_spirit:'martial spirits',mount:'mounts'})[state.equipmentKind];
  grid.className='subsystem-grid';grid.innerHTML='';if(!rows.length){grid.innerHTML='<div class="empty-state"><strong>No records found</strong>Try a different search.</div>';return}
  const tpl=$('#subsystemCardTemplate');for(const s of rows){const n=tpl.content.cloneNode(true),btn=n.querySelector('.subsystem-card'),img=chooseImage(s,'grid_card',['card','icon']);if(img)n.querySelector('.subsystem-art').src=assetSrc(img);n.querySelector('.subsystem-name').textContent=s.name;n.querySelector('.subsystem-meta').textContent=s.subsystem_type==='soul'?(s.profession_fit||[]).map(professionLabel).join(' / ')||'Soul':s.subsystem_type.replace('_',' ');btn.onclick=()=>location.hash='subsystem/'+s.subsystem_type+'/'+encodeURIComponent(s.subsystem_key);grid.appendChild(n)}
}
function modeOptions(current){return Object.entries(rankingModes()).map(([k,v])=>'<option value="'+esc(k)+'" '+(k===current?'selected':'')+'>'+esc(v.label||k)+'</option>').join('')}
function renderRankings(body){
  if(!rankingModes()[state.rankingMode])state.rankingMode=Object.keys(rankingModes())[0]||'general_pve';
  body.innerHTML='<section class="ranking-head"><div><span class="eyebrow">Codex evaluation</span><h2>Character rankings</h2><p>Fixed absolute grades derived from sourced mechanics across explicit axes. No source/community tier is an input and no tier has a quota.</p></div><label class="mode-select"><span>Scenario</span><select id="rankingMode">'+modeOptions(state.rankingMode)+'</select></label></section><div class="axis-legend">'+axisOrder.map(k=>'<span>'+esc(axisLabel(k))+'</span>').join('')+'</div><div id="rankingList" class="ranking-list"></div>';
  $('#rankingMode').onchange=e=>{state.rankingMode=e.target.value;renderRankings(body)};
  const r=rankingFor(state.rankingMode),list=$('#rankingList');if(!r){list.innerHTML='<div class="empty-state"><strong>No ranking data</strong>This adapter has no evaluation for that scenario.</div>';return}
  list.innerHTML=(r.entries||[]).map(row=>{const e=entityById(row.entity_id),img=chooseImage(e,'grid_card',['card','portrait','icon']),axes=scenarioAxes(e,state.rankingMode),top=axisOrder.map(k=>({k,v:Number(axes[k]?.score||0)})).sort((a,b)=>b.v-a.v).slice(0,3);return '<button class="ranking-row" data-id="'+e.id+'"><div class="rank-number">#'+row.rank+'</div>'+(img?'<img src="'+esc(assetSrc(img))+'" alt="">':'<div class="rank-art-empty"></div>')+'<div class="rank-main"><strong>'+esc(displayName(e))+'</strong><span>'+esc(confidenceLabel(row.confidence))+'</span><div class="mini-axis-row">'+top.map(x=>'<i><b style="width:'+Math.round(x.v)+'%"></b><em>'+esc(axisLabel(x.k))+'</em></i>').join('')+'</div></div><div class="rank-grade '+gradeClass(row.grade)+'"><strong>'+esc(row.grade)+'</strong><span>'+Math.round(row.score)+'</span></div></button>'}).join('');
  list.querySelectorAll('.ranking-row').forEach(b=>b.onclick=()=>location.hash='character/'+b.dataset.id);
}
function edgeMap(){const m=new Map();for(const x of catalog.team_optimizer?.synergy_edges||[]){m.set(Math.min(x.a,x.b)+':'+Math.max(x.a,x.b),Number(x.strength||0))}return m}
function teamScore(ids,mode){
  const chars=ids.map(entityById).filter(Boolean),cfg=catalog.team_optimizer||{},edges=edgeMap();if(!chars.length)return {total:0,base:0,synergy:0,coverage:0,redundancy:0};
  const base=chars.reduce((s,e)=>s+Number(scenario(e,mode)?.score||0),0)/chars.length;
  let edgeRaw=0;for(let i=0;i<chars.length;i++)for(let j=i+1;j<chars.length;j++)edgeRaw+=edges.get(Math.min(chars[i].id,chars[j].id)+':'+Math.max(chars[i].id,chars[j].id))||0;
  const synergy=Math.min(Number(catalog.adapter?.team_optimizer?.synergy_bonus_cap||15),edgeRaw*1.6);
  const covAxes=cfg.coverage_axes||['offense','survivability','control','support','disruption','tempo'];let cov=0;
  for(const k of covAxes)cov+=Math.max(...chars.map(e=>Number(scenarioAxes(e,mode)[k]?.score||0)))/100;
  const coverage=Math.min(Number(catalog.adapter?.team_optimizer?.coverage_bonus_cap||12),(cov/covAxes.length)*12);
  let sim=0,pairs=0;for(let i=0;i<chars.length;i++)for(let j=i+1;j<chars.length;j++){const a=scenarioAxes(chars[i],mode),b=scenarioAxes(chars[j],mode);let dot=0,aa=0,bb=0;for(const k of axisOrder){const x=Number(a[k]?.score||0),y=Number(b[k]?.score||0);dot+=x*y;aa+=x*x;bb+=y*y}if(aa&&bb){sim+=dot/Math.sqrt(aa*bb);pairs++}}
  const avgSim=pairs?sim/pairs:0,redundancy=Math.max(0,(avgSim-.82)/.18)*Number(catalog.adapter?.team_optimizer?.duplicate_profile_penalty_cap||8);
  return {total:Math.min(100,Math.max(0,base*.78+synergy+coverage-redundancy)),base,synergy,coverage,redundancy};
}
function optimizeTeam(mode,anchorId=null,excludeId=null,ownedOnly=false){
  const teamSize=Number(catalog.team_optimizer?.team_size||catalog.adapter?.team_size||6),owned=ownedIds();
  let candidates=activeGameEntities().filter(e=>e.id!==excludeId&&(!ownedOnly||owned.has(e.id))&&scenario(e,mode));
  candidates.sort((a,b)=>Number(scenario(b,mode)?.score||0)-Number(scenario(a,mode)?.score||0));
  const pool=Number(catalog.team_optimizer?.candidate_pool||48);candidates=candidates.slice(0,pool);
  if(anchorId&&!candidates.some(e=>e.id===anchorId)){const a=entityById(anchorId);if(a&&a.id!==excludeId&&(!ownedOnly||owned.has(a.id)))candidates.unshift(a)}
  let beams=[anchorId?[anchorId]:[]];const width=Number(catalog.team_optimizer?.beam_width||120);
  while(beams.length&&beams[0].length<teamSize){
    const next=[];for(const team of beams){for(const e of candidates){if(team.includes(e.id))continue;const ids=[...team,e.id];next.push({ids,score:teamScore(ids,mode).total})}}
    next.sort((a,b)=>b.score-a.score);beams=next.slice(0,width).map(x=>x.ids);if(!beams.length)break
  }
  return beams.map(ids=>({ids,components:teamScore(ids,mode)})).sort((a,b)=>b.components.total-a.components.total).slice(0,4);
}
function renderTeams(body){
  if(!rankingModes()[state.teamMode])state.teamMode='general_pve';
  const chars=activeGameEntities().slice().sort((a,b)=>displayName(a).localeCompare(displayName(b))),opts='<option value="">None</option>'+chars.map(e=>'<option value="'+e.id+'">'+esc(displayName(e))+'</option>').join('');
  body.innerHTML='<section class="ranking-head"><div><span class="eyebrow">Team optimizer</span><h2>Build a team</h2><p>Uses scenario performance, mechanic synergy and axis coverage. It never copies site team rankings.</p></div></section><div class="team-controls"><label><span>Scenario</span><select id="teamMode">'+modeOptions(state.teamMode)+'</select></label><label><span>Build around</span><select id="teamAnchor">'+opts+'</select></label><label><span>Exclude</span><select id="teamExclude">'+opts+'</select></label><label class="check-row"><input id="teamOwnedOnly" type="checkbox" '+(state.teamOwnedOnly?'checked':'')+'><span>Use owned roster only</span></label><button class="primary-button" id="runTeam">Optimize team</button></div><div id="teamResults"></div>';
  $('#teamMode').value=state.teamMode;$('#teamAnchor').value=state.teamAnchor||'';$('#teamExclude').value=state.teamExclude||'';$('#teamMode').onchange=e=>state.teamMode=e.target.value;$('#teamAnchor').onchange=e=>state.teamAnchor=e.target.value?Number(e.target.value):null;$('#teamExclude').onchange=e=>state.teamExclude=e.target.value?Number(e.target.value):null;$('#teamOwnedOnly').onchange=e=>state.teamOwnedOnly=e.target.checked;$('#runTeam').onclick=()=>renderTeamResults();
}
function renderTeamResults(){
  const host=$('#teamResults');if(state.teamOwnedOnly&&ownedIds().size<(catalog.adapter?.team_size||6)){host.innerHTML='<div class="empty-state"><strong>Not enough owned characters</strong>Add at least '+(catalog.adapter?.team_size||6)+' characters to your roster.</div>';return}
  const teams=optimizeTeam(state.teamMode,state.teamAnchor,state.teamExclude,state.teamOwnedOnly);if(!teams.length){host.innerHTML='<div class="empty-state"><strong>No valid team</strong>Change the constraints and try again.</div>';return}
  host.innerHTML=teams.map((t,idx)=>'<section class="team-result"><div class="team-result-head"><div><span class="eyebrow">'+(idx===0?'Best match':'Alternative '+idx)+'</span><h3>'+Math.round(t.components.total)+' team index</h3></div><div class="team-components"><span>Base '+Math.round(t.components.base)+'</span><span>Synergy +'+t.components.synergy.toFixed(1)+'</span><span>Coverage +'+t.components.coverage.toFixed(1)+'</span>'+(t.components.redundancy?'<span>Overlap −'+t.components.redundancy.toFixed(1)+'</span>':'')+'</div></div><div class="team-cards">'+t.ids.map(id=>{const e=entityById(id),img=chooseImage(e,'grid_card',['card']);return '<button class="team-member" data-id="'+id+'>'+(img?'<img src="'+esc(assetSrc(img))+'" alt="">':'')+'<strong>'+esc(displayName(e))+'</strong><span>'+esc(scenario(e,state.teamMode)?.grade||'')+'</span></button>'}).join('')+'</div></section>').join('');
  host.querySelectorAll('.team-member').forEach(b=>b.onclick=()=>location.hash='character/'+b.dataset.id);
}
function renderFilters(){const rows=activeGameEntities(),vals=k=>[...new Set(rows.map(e=>e[k]).filter(Boolean))].sort(),professions=[...new Set(rows.flatMap(e=>e.kaisen_meta?.professions||[]))].sort(),options=(arr,current,fmt=x=>x)=>'<option value="">All</option>'+arr.map(v=>'<option value="'+esc(v)+'" '+(current===v?'selected':'')+'>'+esc(fmt(v))+'</option>').join('');$('#filterSheet').innerHTML='<div class="sheet-handle"></div><div class="sheet-head"><h2>Character filters</h2><button class="icon-button" id="closeFilter">×</button></div><div class="sheet-grid"><div class="sheet-field"><label>Rarity</label><select id="fRarity">'+options(vals('rarity_key'),state.filters.rarity)+'</select></div><div class="sheet-field"><label>Faction</label><select id="fFaction">'+options(vals('faction_key'),state.filters.faction)+'</select></div><div class="sheet-field"><label>Attribute</label><select id="fAttribute">'+options(vals('attribute_type'),state.filters.attribute)+'</select></div><div class="sheet-field"><label>Role</label><select id="fProfession">'+options(professions,state.filters.profession,professionLabel)+'</select></div><div class="sheet-field"><label>Sort</label><select id="fSort"><option value="name" '+(state.filters.sort==='name'?'selected':'')+'>Name</option><option value="release" '+(state.filters.sort==='release'?'selected':'')+'>Newest</option><option value="rarity" '+(state.filters.sort==='rarity'?'selected':'')+'>Rarity</option></select></div></div><div class="sheet-actions"><button class="secondary-button" id="clearFilters">Clear</button><button class="primary-button" id="applyFilters">Apply</button></div>';openSheet('filterSheet');$('#closeFilter').onclick=closeSheets;$('#clearFilters').onclick=()=>{state.filters={rarity:'',faction:'',attribute:'',profession:'',sort:'name'};closeSheets();renderGameSection()};$('#applyFilters').onclick=()=>{state.filters.rarity=$('#fRarity').value;state.filters.faction=$('#fFaction').value;state.filters.attribute=$('#fAttribute').value;state.filters.profession=$('#fProfession').value;state.filters.sort=$('#fSort').value;closeSheets();renderGameSection()}}
function renderSettings(){$('#settingsSheet').innerHTML='<div class="sheet-handle"></div><div class="sheet-head"><h2>Game Codex</h2><button class="icon-button" id="closeSettings">×</button></div><div class="settings-actions"><button id="importPack">Import database pack</button><button id="reloadApp">Reload app</button><button id="restorePack">Restore bundled database</button><button id="appInfo">Android app information</button></div><div class="settings-meta">Engine '+esc(catalog.engine_version||'unknown')+' • Adapter '+esc(catalog.adapter?.version||'—')+'<br>Personal roster data is stored locally on this device. Source provenance stays available in character Sources.</div>';openSheet('settingsSheet');$('#closeSettings').onclick=closeSheets;$('#importPack').onclick=()=>{closeSheets();nativeCall('choosePack')};$('#reloadApp').onclick=()=>{closeSheets();nativeCall('reload')};$('#restorePack').onclick=()=>{closeSheets();nativeCall('restoreBundledPack')};$('#appInfo').onclick=()=>{closeSheets();nativeCall('appInfo')}}
