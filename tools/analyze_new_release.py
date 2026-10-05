#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path

AXES=("offense","tempo","survivability","control","support","disruption","reliability","independence","synergy_ceiling","counter_resilience")

def vec(e,mode):
    ev=e.get("codex_evaluation") or {};sc=(ev.get("scenarios") or {}).get(mode) or {}
    axes=sc.get("optimized_axes") or (ev.get("axes") or {}).get("base") or {}
    return [float((axes.get(k) or {}).get("score",0)) for k in AXES]

def dist(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def main():
    ap=argparse.ArgumentParser();ap.add_argument("catalog");ap.add_argument("--entity-key",required=True);ap.add_argument("--out",required=True);args=ap.parse_args()
    c=json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    entities=c.get("entities") or [];target=next((e for e in entities if e.get("entity_key")==args.entity_key),None)
    if not target:raise SystemExit("entity not found")
    impacts={}
    for mode in [r.get("mode_key") for r in c.get("rankings") or []]:
        tv=vec(target,mode);neighbors=[]
        for e in entities:
            if e["id"]==target["id"]:continue
            d=dist(tv,vec(e,mode));neighbors.append((d,e))
        neighbors.sort(key=lambda x:x[0])
        impacts[mode]={
          "closest_substitutes":[{"entity_id":e["id"],"name":e.get("display_name") or e.get("canonical_name"),"distance":round(d,2)} for d,e in neighbors[:8]],
          "target":{"rank":(target.get("codex_evaluation") or {}).get("scenarios",{}).get(mode,{}).get("rank"),"grade":(target.get("codex_evaluation") or {}).get("scenarios",{}).get(mode,{}).get("grade"),"score":(target.get("codex_evaluation") or {}).get("scenarios",{}).get(mode,{}).get("score")}
        }
    edges=[x for x in c.get("compatibility") or [] if x.get("from_entity_id")==target["id"] or x.get("to_entity_id")==target["id"]]
    edges.sort(key=lambda x:-abs(float(x.get("score") or 0)))
    report={"entity_key":target["entity_key"],"name":target.get("display_name") or target.get("canonical_name"),"modes":impacts,"strongest_relationships":edges[:20],"source_tiers_used":False}
    Path(args.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"entity":report["name"],"modes":len(impacts),"relationships":len(edges[:20])},ensure_ascii=False))
if __name__=="__main__":main()
