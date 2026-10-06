function cosine(a,b){
  let dot=0,aa=0,bb=0;
  for(let i=0;i<a.length;i++){const x=Number(a[i]||0),y=Number(b[i]||0);dot+=x*y;aa+=x*x;bb+=y*y}
  return aa&&bb?dot/Math.sqrt(aa*bb):0;
}
function edgeKey(a,b){return Math.min(a,b)+':'+Math.max(a,b)}
function teamComponents(ids,ctx){
  const members=ids.map(id=>ctx.byId.get(id)).filter(Boolean);
  if(!members.length)return {total:0,base:0,synergy:0,coverage:0,redundancy:0};
  const base=members.reduce((s,m)=>s+m.score,0)/members.length;
  let edgeRaw=0;
  for(let i=0;i<members.length;i++)for(let j=i+1;j<members.length;j++)edgeRaw+=ctx.edges.get(edgeKey(members[i].id,members[j].id))||0;
  const synergy=Math.min(ctx.synergyBonusCap,edgeRaw*1.6);
  let cov=0;
  for(const idx of ctx.coverageAxes){
    let best=0;for(const m of members)best=Math.max(best,Number(m.axes[idx]||0));cov+=best/100;
  }
  const coverage=Math.min(ctx.coverageBonusCap,(cov/Math.max(1,ctx.coverageAxes.length))*ctx.coverageBonusCap);
  let sim=0,pairs=0;
  for(let i=0;i<members.length;i++)for(let j=i+1;j<members.length;j++){sim+=cosine(members[i].axes,members[j].axes);pairs++}
  const avg=pairs?sim/pairs:0;
  const redundancy=Math.max(0,(avg-.82)/.18)*ctx.redundancyPenaltyCap;
  return {total:Math.min(100,Math.max(0,base*.78+synergy+coverage-redundancy)),base,synergy,coverage,redundancy};
}
function signature(ids){return ids.slice().sort((a,b)=>a-b).join(',')}
function optimize(payload){
  const byId=new Map((payload.candidates||[]).map(x=>[Number(x.id),x]));
  const edges=new Map((payload.edges||[]).map(x=>[edgeKey(Number(x.a),Number(x.b)),Number(x.strength||0)]));
  const ctx={byId,edges,coverageAxes:payload.coverageAxes||[],synergyBonusCap:Number(payload.synergyBonusCap||15),coverageBonusCap:Number(payload.coverageBonusCap||12),redundancyPenaltyCap:Number(payload.redundancyPenaltyCap||8)};
  const teamSize=Number(payload.teamSize||6),fixed=[...new Set((payload.fixedIds||[]).map(Number))].filter(id=>byId.has(id)),fixedSet=new Set(fixed);
  if(fixed.length>teamSize)return [];
  const candidates=[...byId.values()].sort((a,b)=>b.score-a.score);
  let beams=[{ids:fixed,components:teamComponents(fixed,ctx)}],seen=new Set([signature(fixed)]);
  const width=Math.max(12,Math.min(Number(payload.beamWidth||72),120));
  let depth=fixed.length;
  while(depth<teamSize){
    const next=[];
    const stageSeen=new Set();
    for(const beam of beams){
      for(const c of candidates){
        if(beam.ids.includes(c.id))continue;
        const ids=[...beam.ids,c.id],sig=signature(ids);
        if(stageSeen.has(sig))continue;
        stageSeen.add(sig);
        const components=teamComponents(ids,ctx);
        next.push({ids,components});
      }
    }
    next.sort((a,b)=>b.components.total-a.components.total);
    beams=next.slice(0,width);
    depth++;
    postMessage({type:'progress',depth,label:'Evaluating team slot '+depth+' of '+teamSize+'…'});
    if(!beams.length)break;
  }
  const out=[],finalSeen=new Set();
  for(const row of beams){
    if(row.ids.length!==teamSize)continue;
    const sig=signature(row.ids);if(finalSeen.has(sig))continue;finalSeen.add(sig);out.push(row);
    if(out.length>=4)break;
  }
  return out;
}
onmessage=function(e){
  const p=e.data||{};
  try{
    if(p.op!=='optimize')throw new Error('Unknown optimizer operation');
    postMessage({type:'progress',depth:(p.fixedIds||[]).length,label:'Preparing '+(p.candidates||[]).length+' candidates…'});
    const teams=optimize(p);
    postMessage({type:'result',teams});
  }catch(err){
    postMessage({type:'error',message:String(err&&err.message||err)});
  }
};