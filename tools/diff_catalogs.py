#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def load(path):
    p=Path(path)
    if p.is_dir():p=p/"data/catalog.json"
    return json.loads(p.read_text(encoding="utf-8"))

def skill_fingerprint(e):
    return [(s.get("skill_key"),s.get("name"),s.get("description_source"),[(ef.get("effect_type"),ef.get("mechanic_key"),ef.get("magnitude"),ef.get("condition"),ef.get("timing")) for v in s.get("versions") or [] for ef in v.get("effects") or []]) for s in e.get("skills") or []]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("old");ap.add_argument("new");ap.add_argument("--out",required=True);args=ap.parse_args()
    old,new=load(args.old),load(args.new)
    oa={e["entity_key"]:e for e in old.get("entities") or []};na={e["entity_key"]:e for e in new.get("entities") or []}
    added=sorted(set(na)-set(oa));removed=sorted(set(oa)-set(na));changed=[]
    for k in sorted(set(oa)&set(na)):
        diffs=[]
        for field in ("canonical_name","display_name","rarity_key","faction_key","attribute_type"):
            if oa[k].get(field)!=na[k].get(field):diffs.append({"field":field,"before":oa[k].get(field),"after":na[k].get(field)})
        if skill_fingerprint(oa[k])!=skill_fingerprint(na[k]):diffs.append({"field":"kit","before_skill_count":len(oa[k].get("skills") or []),"after_skill_count":len(na[k].get("skills") or [])})
        if diffs:
            before=(oa[k].get("codex_evaluation") or {}).get("scenarios") or {};after=(na[k].get("codex_evaluation") or {}).get("scenarios") or {}
            movement={}
            for mode in set(before)|set(after):
                b,a=before.get(mode) or {},after.get(mode) or {}
                if b.get("rank")!=a.get("rank") or b.get("grade")!=a.get("grade") or b.get("score")!=a.get("score"):
                    movement[mode]={"before":{"rank":b.get("rank"),"grade":b.get("grade"),"score":b.get("score")},"after":{"rank":a.get("rank"),"grade":a.get("grade"),"score":a.get("score")}}
            changed.append({"entity_key":k,"name":na[k].get("display_name") or na[k].get("canonical_name"),"changes":diffs,"evaluation_movement":movement})
    report={"old_engine":old.get("engine_version"),"new_engine":new.get("engine_version"),"added":[{"entity_key":k,"name":na[k].get("display_name") or na[k].get("canonical_name")} for k in added],"removed":[{"entity_key":k,"name":oa[k].get("display_name") or oa[k].get("canonical_name")} for k in removed],"changed":changed}
    Path(args.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"added":len(added),"removed":len(removed),"changed":len(changed)},ensure_ascii=False))
if __name__=="__main__":main()
