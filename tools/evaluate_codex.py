#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math
from collections import defaultdict
from pathlib import Path

AXES=("offense","tempo","survivability","control","support","disruption","reliability","independence","synergy_ceiling","counter_resilience")

def pct(effect):
    m=effect.get("magnitude") or {}
    if m.get("percent") is not None:
        try:return abs(float(m["percent"]))
        except:return 0.0
    vals=[]
    for x in m.get("percent_values") or []:
        try:vals.append(abs(float(x)))
        except:pass
    return max(vals,default=0.0)

def breadth(effect):
    t=effect.get("target") or {}
    if t.get("scope") in ("all","random"):return 6.0
    try:return max(1.0,min(6.0,float(t.get("count") or 1)))
    except:return 1.0

def effects(entity,extras=None):
    out=[]
    for skill in entity.get("skills") or []:
        if skill.get("analysis_eligible") is False:continue
        for version in skill.get("versions") or []:
            out.extend(version.get("effects") or [])
    for sub in extras or []:
        out.extend((sub.get("max_profile") or {}).get("effects") or [])
    return out

def hero_key(entity):
    stem=(entity.get("asset_stem") or entity.get("entity_key","").split(":")[-1]).split("/")[-1]
    if stem.startswith("herocard_"):stem=stem[len("herocard_"):]
    while stem and stem[-1].isdigit():stem=stem[:-1]
    return stem

def compatible(entity,subsystems,kind):
    rows=[s for s in subsystems if s.get("subsystem_type")==kind]
    if kind=="soul":
        prof=set((entity.get("kaisen_meta") or {}).get("professions") or [])
        return [s for s in rows if not s.get("profession_fit") or prof.intersection(s.get("profession_fit") or [])]
    if kind=="martial_spirit":
        hk=hero_key(entity)
        return [s for s in rows if hk in set((s.get("compatibility") or {}).get("hero_keys") or [])]
    return rows

def clamp01(x):return max(0.0,min(1.0,float(x)))
def scale(raw,reference):
    if reference<=0:return 0.0
    return min(100.0,max(0.0,100.0*raw/reference))

def analyze_axes(entity,adapter,extras=None):
    rows=effects(entity,extras)
    total=max(1,len(rows));unconditional=0;self_positive=0;team_positive=0
    direct_damage=0.0;off_amp=0.0;bypass=0.0;tempo=0.0;sustain=0.0
    control=0.0;support=0.0;disruption=0.0;resilience=0.0
    provides=set();conditional_needs=set();families=set();evidence=defaultdict(list)

    for ef in rows:
        et=ef.get("effect_type") or "";mk=ef.get("mechanic_key") or "";p=pct(ef);b=breadth(ef)
        m=ef.get("magnitude") or {};target=ef.get("target") or {};cond=ef.get("condition") or {};timing=ef.get("timing") or {}
        conditional=bool(cond);unconditional += 0 if conditional else 1
        side=target.get("side")
        if conditional:
            conditional_needs.add(mk or et)
        if side=="self" and ef.get("polarity")=="positive":self_positive+=1
        if side=="ally" and ef.get("polarity")=="positive":team_positive+=1

        if et=="damage":
            hits=max(1.0,float(m.get("hits") or 1))
            mult=1.0
            if mk in ("true_damage","piercing_damage"):mult=1.15;bypass+=1
            v=p*hits*b*mult
            direct_damage+=v;families.add("damage")
            evidence["offense"].append({"mechanic":mk or "damage","value":round(v,2)})
        if mk in ("attack_up","damage_up","crit_damage_up","crit_rate_up","penetration_up","normal_attack_multiplier"):
            if mk=="normal_attack_multiplier":
                val=max(0.0,float(m.get("multiplier") or 1)-1)*100
            else:val=p
            off_amp+=val
            evidence["offense"].append({"mechanic":mk,"value":round(val,2)})
        if mk in ("defense_ignore","protection_ignore","defensive_immunity"):bypass+=1.5

        if et=="trigger" or mk in ("extra_skill_cast","extra_action","action_advance"):
            tempo+=2.0;families.add("tempo");evidence["tempo"].append({"mechanic":mk or et,"value":2.0})
        if timing.get("trigger") in ("round_start","on_enter","on_action"):
            tempo+=0.5;evidence["tempo"].append({"mechanic":"automatic trigger","value":0.5})
        if et in ("resource_generate",):
            tempo+=0.35*b;families.add("resource");evidence["tempo"].append({"mechanic":mk or et,"value":round(0.35*b,2)})

        if et in ("heal","shield"):
            v=1.0+min(p,300)/100*(0.5+0.5*b/6)
            sustain+=v;families.add("sustain");evidence["survivability"].append({"mechanic":mk or et,"value":round(v,2)})
            if side=="ally":support+=v
        if et=="revive":
            sustain+=3.0;resilience+=2.0;families.add("sustain")
            evidence["survivability"].append({"mechanic":"revive","value":3.0})
        if et=="immunity":
            sustain+=2.0;resilience+=2.0;families.add("sustain")
            evidence["counter_resilience"].append({"mechanic":mk or "immunity","value":2.0})
        if mk in ("hp_up","defense_up","block_rate_up","damage_reduction","lifesteal_up","physical_resist_up","magic_resist_up"):
            v=min(p,300)/100
            sustain+=v
            evidence["survivability"].append({"mechanic":mk,"value":round(v,2)})

        if et=="debuff":
            v=0.8+min(p,200)/200+0.25*(b/6)
            control+=v;families.add("control");evidence["control"].append({"mechanic":mk or "debuff","value":round(v,2)})
            provides.add(mk or "debuff")
        if et=="extension" and (ef.get("extension") or {}).get("source_status_name"):
            provides.add(mk or "status")
            control+=0.35
        if mk in ("crit_disable","stun","silence","freeze","confusion","heal_block"):
            control+=0.8

        if et=="buff":
            v=0.5+min(p,300)/250
            if side=="ally":v*=1.25
            support+=v;families.add("support");evidence["support"].append({"mechanic":mk or "buff","value":round(v,2)})
            provides.add(mk or "buff")
        if et=="cleanse":
            support+=1.4;resilience+=1.3;families.add("support")
            evidence["support"].append({"mechanic":"cleanse","value":1.4})
        if et=="resource_generate" and side=="ally":
            support+=0.8
        if et=="dispel":
            disruption+=1.5;families.add("disruption");evidence["disruption"].append({"mechanic":"dispel","value":1.5})
        if et=="counter":
            disruption+=1.5;families.add("disruption");evidence["disruption"].append({"mechanic":mk or "counter","value":1.5})
        if et=="resource_consume":
            disruption+=1.0
        if mk in ("heal_block","defense_ignore","protection_ignore","crit_disable","damage_taken_up"):
            disruption+=1.0
        if et=="cleanse":resilience+=1.1
        if mk in ("status_resist_up","guaranteed_hit","guaranteed_crit"):
            resilience+=0.7
        if mk in ("death_prevention","damage_immunity"):
            resilience+=1.4

    # Reliability is a ratio rather than a count. Guaranteed targeting/hit can lift it;
    # random/conditional mechanics reduce it.
    base_reliability=unconditional/total
    random_penalty=sum(1 for e in rows if (e.get("target") or {}).get("scope")=="random")/total
    guaranteed=sum(1 for e in rows if e.get("mechanic_key") in ("guaranteed_hit","guaranteed_crit"))/max(1,total)
    reliability=clamp01(base_reliability-0.25*random_penalty+0.20*guaranteed)

    self_enable=(self_positive+sum(1 for e in rows if e.get("effect_type")=="resource_generate" and (e.get("target") or {}).get("side") in ("self",None)))/total
    independence=clamp01(0.55*base_reliability+0.45*min(1.0,self_enable*2))

    spirit_count=len(compatible(entity,extras or [],"martial_spirit")) if extras else 0
    synergy_raw=len(provides)*0.65+team_positive*0.35+len(families)*0.35+min(4,spirit_count)*0.25

    raw={
      "offense":direct_damage+off_amp*7.0+bypass*450.0,
      "tempo":tempo,
      "survivability":sustain,
      "control":control,
      "support":support,
      "disruption":disruption,
      "reliability":reliability,
      "independence":independence,
      "synergy_ceiling":synergy_raw,
      "counter_resilience":resilience,
    }
    result={}
    for axis in AXES:
        ref=float(adapter["axes"][axis]["reference"])
        result[axis]={
          "score":round(scale(raw[axis],ref),2),
          "raw":round(raw[axis],4),
          "reference":ref,
          "label":adapter["axes"][axis]["label"],
          "evidence":sorted(evidence.get(axis,[]),key=lambda x:-abs(float(x.get("value") or 0)))[:8],
        }
    result["_meta"]={"effect_count":len(rows),"unconditional_effects":unconditional,"families":sorted(families),"team_positive_effects":team_positive,"self_positive_effects":self_positive}
    return result

def axis_score(axes,weights):
    denom=sum(float(v) for v in weights.values()) or 1.0
    return sum(float(weights.get(k,0))*float((axes.get(k) or {}).get("score",0)) for k in weights)/denom

def grade(score,thresholds):
    for row in thresholds:
        if score>=float(row["min"]):return row["grade"]
    return "D"

def loadout_options(entity,subs):
    return [
      ("soul",compatible(entity,subs,"soul")),
      ("martial_spirit",compatible(entity,subs,"martial_spirit")),
      ("mount",compatible(entity,subs,"mount")),
    ]

def optimize_loadout(entity,subs,adapter,weights):
    selected=[];base=analyze_axes(entity,adapter,selected);best_score=axis_score(base,weights);evaluated=0
    for kind,options in loadout_options(entity,subs):
        local=(best_score,None,base)
        for candidate in options:
            axes=analyze_axes(entity,adapter,selected+[candidate]);score=axis_score(axes,weights);evaluated+=1
            if score>local[0]+1e-9:local=(score,candidate,axes)
        if local[1] is not None:
            selected.append(local[1]);best_score,_,base=local
    return selected,base,best_score,evaluated

def character_confidence(entity):
    skills=entity.get("skills") or []
    if not skills:return 0.0
    valid=0;total=0
    for s in skills:
        if s.get("presentation_class")=="source_note":continue
        total+=1
        if any(v.get("effects") for v in s.get("versions") or []):valid+=1
    coverage=valid/max(1,total)
    provenance=min(1.0,len(entity.get("provenance") or [])/2)
    return round(0.75*coverage+0.25*provenance,3)

def mechanics_signature(entity):
    sig=set()
    for ef in effects(entity):
        mk=ef.get("mechanic_key");et=ef.get("effect_type")
        if mk:sig.add(mk)
        elif et:sig.add(et)
    return sig

def replacement_values(entities):
    sigs={e["id"]:mechanics_signature(e) for e in entities}
    out={}
    for e in entities:
        a=sigs[e["id"]]
        best=None
        for other in entities:
            if other["id"]==e["id"]:continue
            b=sigs[other["id"]]
            if not a and not b:similarity=1.0
            else:similarity=len(a&b)/max(1,len(a|b))
            if best is None or similarity>best[0]:best=(similarity,other)
        similarity=best[0] if best else 0.0
        uniqueness=round(100*(1-similarity),2)
        out[e["id"]]={"uniqueness":uniqueness,"nearest_substitute_id":best[1]["id"] if best else None,"mechanic_similarity":round(similarity,4)}
    return out

def build_team_optimizer(catalog,adapter):
    entities=catalog.get("entities") or [];edges=catalog.get("compatibility") or []
    edge_map={}
    for x in edges:
        a=int(x.get("from_entity_id"));b=int(x.get("to_entity_id"));edge_map[(min(a,b),max(a,b))]=max(abs(float(x.get("score") or 0)),edge_map.get((min(a,b),max(a,b)),0))
    return {
      "version":"1.0.0",
      "team_size":adapter["team_optimizer"]["team_size"],
      "candidate_pool":adapter["team_optimizer"]["candidate_pool"],
      "beam_width":adapter["team_optimizer"]["beam_width"],
      "synergy_edges":[{"a":a,"b":b,"strength":round(v,3)} for (a,b),v in sorted(edge_map.items())],
      "coverage_axes":["offense","survivability","control","support","disruption","tempo"],
      "source_tiers_used":False,
      "notes":["Team optimization uses Codex scenario evaluations plus normalized compatibility evidence and axis coverage.","Owned-roster constraints are applied locally on device and never alter sourced game data."]
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    ap.add_argument("--adapter",required=True)
    args=ap.parse_args()
    root=Path(args.out);catalog_path=root/"data/catalog.json"
    catalog=json.loads(catalog_path.read_text(encoding="utf-8"))
    adapter=json.loads(Path(args.adapter).read_text(encoding="utf-8"))
    entities=catalog.get("entities") or [];subs=catalog.get("subsystems") or []
    replacement=replacement_values(entities)

    rankings=[]
    for e in entities:
        base_axes=analyze_axes(e,adapter,[])
        evaluation={
          "version":"1.0.0","status":"production","source_tiers_used":False,
          "confidence":character_confidence(e),
          "axes":{"base":base_axes},
          "scenarios":{},
          "replacement_value":replacement[e["id"]],
        }
        e["codex_evaluation"]=evaluation

    for mode,mcfg in adapter["modes"].items():
        rows=[]
        weights=mcfg["axis_weights"]
        for e in entities:
            base_axes=e["codex_evaluation"]["axes"]["base"]
            base_score=axis_score(base_axes,weights)
            selected,opt_axes,opt_score,evaluated=optimize_loadout(e,subs,adapter,weights)
            profile=mcfg.get("profile","optimized")
            chosen_score=base_score if profile=="base" else opt_score
            chosen_axes=base_axes if profile=="base" else opt_axes
            row={
              "mode_key":mode,"label":mcfg["label"],"description":mcfg["description"],
              "score":round(chosen_score,2),"grade":grade(chosen_score,adapter["grade_thresholds"]),
              "profile":profile,"confidence":e["codex_evaluation"]["confidence"],
              "base_score":round(base_score,2),"optimized_score":round(opt_score,2),
              "optimized_axes":opt_axes,
              "selected_subsystems":[{"type":x["subsystem_type"],"key":x["subsystem_key"],"name":x["name"]} for x in selected],
              "candidates_evaluated":evaluated,
              "axis_weights":weights,
            }
            e["codex_evaluation"]["scenarios"][mode]=row
            rows.append((chosen_score,e,row))
        rows.sort(key=lambda x:(-x[0],x[1]["id"]))
        entries=[]
        for rank,(_,e,row) in enumerate(rows,1):
            row["rank"]=rank
            entries.append({"entity_id":e["id"],"name":e.get("display_name") or e.get("canonical_name"),"rank":rank,"score":row["score"],"grade":row["grade"],"confidence":row["confidence"],"profile":row["profile"]})
        rankings.append({"ranking_key":"codex_v1","mode_key":mode,"label":mcfg["label"],"description":mcfg["description"],"source_tiers_used":False,"entries":entries})

    catalog["rankings"]=rankings
    catalog["team_optimizer"]=build_team_optimizer(catalog,adapter)
    catalog["adapter"]={"game_key":adapter["game_key"],"version":adapter["adapter_version"],"team_size":adapter["team_size"],"axes":adapter["axes"],"modes":adapter["modes"],"grade_thresholds":adapter["grade_thresholds"]}
    catalog["analysis_policy"]={
      "status":"production_v1",
      "source_tier_inputs":False,
      "ranking_basis":"normalized sourced mechanics + adapter-defined absolute axis benchmarks",
      "tier_quota":False,
      "notes":adapter.get("notes") or []
    }
    catalog["engine_version"]="1.0.0"
    # Keep legacy analysis only for audit, never as active rankings.
    for e in entities:
        e["analysis"]=[a for a in e.get("analysis",[]) if a.get("ranking_key") not in ("codex_analytical","codex_v1")]
    catalog["tier_lists"]=[x for x in catalog.get("tier_lists",[]) if x.get("ranking_key")!="codex_analytical"]

    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (root/"data/catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(catalog,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    report={
      "engine_version":"1.0.0","characters":len(entities),"rankings":len(rankings),
      "all_characters_evaluated":sum(1 for e in entities if e.get("codex_evaluation")),
      "source_tiers_used":False,"tier_quota":False,
      "avg_confidence":round(sum(e["codex_evaluation"]["confidence"] for e in entities)/max(1,len(entities)),3)
    }
    (root/"evaluation-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()
