let catalog={games:[],entities:[],patches:[],compatibility:[],roster_accounts:[]};
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const parse=v=>{try{return JSON.parse(v||'{}')}catch{return v}};
const ids=['search','gameFilter','factionFilter','rarityFilter','attributeFilter','mechanicFilter','roleFilter','accountFilter','ownedFilter','sortFilter'];

function fill(sel,values){for(const v of [...new Set(values.filter(Boolean))].sort()){const o=document.createElement('option');o.value=v;o.textContent=v;$(sel).appendChild(o)}}
function gameName(id){return catalog.games.find(g=>g.id===id)?.name||''}
function bestAnalysis(e){return (e.analysis||[]).filter(x=>x.tier_label&&x.tier_label!=='UNRANKED').sort((a,b)=>Number(a.rank_order||1e9)-Number(b.rank_order||1e9))[0]||null}
function ownedFor(e,account){const rows=(e.roster||[]).filter(r=>!account||String(r.account_id)===String(account));return rows.some(r=>Number(r.owned)===1)}
function searchable(e){return [e.canonical_name,e.entity_key,e.role_key,e.faction_key,e.rarity_key,e.attribute_type,...(e.aliases||[]),...(e.skills||[]).flatMap(s=>[s.name,s.skill_type]),...(e.signals||[]).flatMap(s=>[s.signal_type,s.mechanic_key])].join(' ').toLowerCase()}
function usableAsset(x){return x&&(x.pack_path||x.local_path)}
function assetSrc(x){if(!x)return'';if(x.pack_path)return x.pack_path;const p=x.local_path||'';return p.startsWith('assets/')?p:'assets/'+p.split(/[\\/]/).pop()}
function chooseImage(e,role,types=[]){const imgs=(e.images||[]).filter(usableAsset).sort((a,b)=>Number(b.priority||0)-Number(a.priority||0));return imgs.find(x=>x.display_role===role)||types.map(t=>imgs.find(x=>x.asset_type===t)).find(Boolean)||imgs[0]||null}
function filtered(){
 const q=$('#search').value.trim().toLowerCase(), acct=$('#accountFilter').value, ownership=$('#ownedFilter').value, mech=$('#mechanicFilter').value;
 const arr=catalog.entities.filter(e=>{const owned=ownedFor(e,acct);return(!q||searchable(e).includes(q))&&(!$('#gameFilter').value||gameName(e.game_id)===$('#gameFilter').value)&&(!$('#roleFilter').value||e.role_key===$('#roleFilter').value)&&(!$('#factionFilter').value||e.faction_key===$('#factionFilter').value)&&(!$('#rarityFilter').value||e.rarity_key===$('#rarityFilter').value)&&(!$('#attributeFilter').value||e.attribute_type===$('#attributeFilter').value)&&(!mech||(e.signals||[]).some(s=>s.mechanic_key===mech))&&(!ownership||(ownership==='owned'?owned:!owned));});
 const sort=$('#sortFilter').value;
 arr.sort((a,b)=>sort==='analysis'?(Number(bestAnalysis(a)?.rank_order||1e9)-Number(bestAnalysis(b)?.rank_order||1e9)||a.canonical_name.localeCompare(b.canonical_name)):sort==='rarity'?String(b.rarity_key||'').localeCompare(String(a.rarity_key||''))||a.canonical_name.localeCompare(b.canonical_name):a.canonical_name.localeCompare(b.canonical_name));
 return arr;
}
function render(){
 const arr=filtered(),grid=$('#grid');$('#count').textContent=`${arr.length} character${arr.length===1?'':'s'}`;grid.innerHTML='';
 if(!arr.length){grid.innerHTML='<div class="empty-state"><h2>No characters loaded</h2><p>Import or refresh a Game Codex pack to populate this database.</p></div>';return}
 for(const e of arr){const n=$('#cardTemplate').content.cloneNode(true),article=n.querySelector('.character-card'),img=chooseImage(e,'grid_card',['card','portrait','icon']);
  if(img){const im=n.querySelector('.card-image');im.src=assetSrc(img);im.alt=e.canonical_name;im.classList.remove('hidden')}else n.querySelector('.card-placeholder').classList.remove('hidden');
  n.querySelector('.card-name').textContent=e.canonical_name;n.querySelector('.rarity').textContent=e.rarity_key||'';n.querySelector('.sub').textContent=[e.attribute_type,e.faction_key,e.role_key].filter(Boolean).join(' • ')||'Kit data pending';
  const a=bestAnalysis(e);n.querySelector('.rankline').textContent=a?`Codex ${a.tier_label} • #${a.rank_order}`:'Codex tier pending';article.onclick=()=>location.hash='entity/'+e.id;grid.appendChild(n)}
}
function entityName(id){return catalog.entities.find(x=>x.id===id)?.canonical_name||'#'+id}
function compatFor(id){return (catalog.compatibility||[]).filter(x=>x.from_entity_id===id||x.to_entity_id===id).sort((a,b)=>Math.abs(Number(b.score))-Math.abs(Number(a.score))).slice(0,12)}
function visualPanel(e){const primary=chooseImage(e,'detail_primary',['full_art','splash','portrait','card']),all=(e.images||[]).filter(usableAsset).sort((a,b)=>Number(b.priority||0)-Number(a.priority||0));const main=primary?`<img class="detail-art" src="${esc(assetSrc(primary))}" alt="${esc(e.canonical_name)}"/>`:'<div class="detail-art placeholder">Visual not cached yet</div>';const thumbs=all.filter(x=>!primary||x.id!==primary.id).slice(0,8).map(x=>`<img class="alt-art" src="${esc(assetSrc(x))}" alt="${esc(x.asset_type||'visual')}"/>`).join('');return `<div class="visual-panel">${main}${thumbs?'<div class="alt-strip">'+thumbs+'</div>':''}</div>`}
function showDetail(id){
 const e=catalog.entities.find(x=>x.id===id);if(!e){location.hash='';return}
 $('#grid').classList.add('hidden');const d=$('#detail');d.classList.remove('hidden');
 const skills=(e.skills||[]).map(s=>`<div class="skill"><h3>${esc(s.name||s.skill_key)} <span class="muted">${esc(s.skill_type||'')}</span></h3>${(s.versions||[]).map(v=>(v.effects||[]).map(x=>`<span class="pill">${esc(x.effect_type)}${x.mechanic_key?' · '+esc(x.mechanic_key):''}</span>`).join('')).join('')}</div>`).join('')||'<div class="muted">Kit data not normalized yet.</div>';
 const signals=(e.signals||[]).map(s=>`<span class="pill">${esc(s.signal_type)} → ${esc(s.mechanic_key)}</span>`).join('');
 const analysis=(e.analysis||[]).map(a=>`<li><strong>${esc(a.title||a.mode_key||'Codex')}: ${esc(a.tier_label||'UNRANKED')}</strong>${a.rank_order?' • #'+esc(a.rank_order):''}${a.total_score!=null?' • '+Number(a.total_score).toFixed(2)+'/100':''}<details><summary>Factors / evidence</summary><pre>${esc(JSON.stringify({factors:parse(a.factors_json),evidence:parse(a.evidence_json)},null,2))}</pre></details></li>`).join('')||'<li class="muted">Analytical ranking pending normalized kit data.</li>';
 const opinions=(e.source_opinions||[]).map(o=>`<li>${esc(o.title||'Source')}: <strong>${esc(o.tier_label)}</strong></li>`).join('')||'<li class="muted">No imported source-tier reference.</li>';
 const prov=(e.provenance||[]).map(p=>`<li><strong>${esc(p.site_name)}</strong> — ${esc(p.fact_key)}<br><span class="muted">${esc(p.url||'')} ${p.retrieved_at?'• '+esc(p.retrieved_at):''}</span></li>`).join('')||'<li class="muted">No provenance rows.</li>';
 const compat=compatFor(id).map(x=>`<li><strong>${Number(x.score)>=0?'synergy':'conflict'} ${esc(x.score)}</strong> — ${esc(entityName(x.from_entity_id===id?x.to_entity_id:x.from_entity_id))}</li>`).join('')||'<li class="muted">Compatibility analysis pending.</li>';
 d.innerHTML=`<button class="back" onclick="location.hash=''">← Back</button><div class="character-layout">${visualPanel(e)}<div class="character-data"><h2>${esc(e.canonical_name)}</h2><p>${esc([e.attribute_type,e.faction_key,e.rarity_key,e.role_key].filter(Boolean).join(' • '))}</p><div class="pill-row">${signals}</div><div class="section"><h3>Skills / normalized effects (Layer B)</h3>${skills}</div><div class="section"><h3>Compatibility (Layer D)</h3><ul>${compat}</ul></div><div class="section"><h3>Codex analytical tier (Layer D)</h3><p class="muted">Computed from normalized kit mechanics only. Site/community tiers are never scoring inputs.</p><ul>${analysis}</ul></div><div class="section"><h3>Source/community tiers — reference only (Layer C)</h3><ul>${opinions}</ul></div><div class="section"><h3>Source provenance</h3><ul>${prov}</ul></div></div></div>`;
}
function route(){const m=location.hash.match(/^#entity\/(\d+)$/);if(m)showDetail(Number(m[1]));else{$('#detail').classList.add('hidden');$('#grid').classList.remove('hidden');render()}}
async function boot(){
 catalog=window.CODEX_CATALOG||await (await fetch('data/catalog.json')).json();
 $('#meta').textContent=`${catalog.games.length} game(s) • ${catalog.entities.length} characters • generated ${catalog.generated_at}`;
 fill('#gameFilter',catalog.games.map(x=>x.name));fill('#roleFilter',catalog.entities.map(x=>x.role_key));fill('#factionFilter',catalog.entities.map(x=>x.faction_key));fill('#rarityFilter',catalog.entities.map(x=>x.rarity_key));fill('#attributeFilter',catalog.entities.map(x=>x.attribute_type));fill('#mechanicFilter',catalog.entities.flatMap(x=>(x.signals||[]).map(s=>s.mechanic_key)));
 for(const a of catalog.roster_accounts||[]){const o=document.createElement('option');o.value=a.id;o.textContent=a.label||a.account_key;$('#accountFilter').appendChild(o)}
 for(const id of ids)$('#'+id).addEventListener('input',render);$('#clear').onclick=()=>{for(const id of ids)$('#'+id).value=id==='sortFilter'?'name':'';render()};window.addEventListener('hashchange',route);route()
}
boot().catch(err=>{document.body.innerHTML='<pre>Failed to load Codex: '+esc(err.stack||err)+'</pre>'});
