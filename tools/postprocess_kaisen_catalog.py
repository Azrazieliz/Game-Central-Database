#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from enrich_kaisen_systems import normalize_source_text, compute_rankings

def effect_count(entity):
    return sum(len(v.get("effects") or []) for s in entity.get("skills") or [] for v in s.get("versions") or [])

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);args=ap.parse_args()
    root=Path(args.out);data=root/"data";p=data/"catalog.json"
    cat=json.loads(p.read_text(encoding="utf-8"))
    repaired=[]
    for e in cat.get("entities") or []:
        before=effect_count(e)
        if before==0:
            for s in e.get("skills") or []:
                desc=s.get("description_source") or ""
                eff=normalize_source_text(desc)
                if not s.get("versions"):s["versions"]=[{"effects":eff}]
                elif eff:s["versions"][0]["effects"]=eff
            after=effect_count(e)
            if after>0:
                e["analysis_normalization_fallback"]={"source":"Kaisen Wiki skill text","language":"ja","reason":"English ontology produced no effects; Japanese ontology fallback applied","effects_added":after}
                repaired.append({"entity_id":e["id"],"name":e["canonical_name"],"effects_added":after})
    cat["tier_lists"]=compute_rankings(cat.get("entities") or [],cat.get("subsystems") or [])
    cat["engine_version"]="0.7.1"
    ranked=sum(any(a.get("ranking_key")=="codex_analytical" and a.get("profile_key")=="optimized_subsystems" and a.get("tier_label")!="UNRANKED" for a in e.get("analysis",[])) for e in cat.get("entities") or [])
    report_path=root/"kaisen-system-enrichment-report.json"
    report=json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    report.update({"engine_version":"0.7.1","japanese_skill_fallback_characters":repaired,"heroes_ranked_with_subsystems":ranked,"source_tiers_used_for_analysis":False})
    if cat.get("games"):
        cat["games"][0]["data_report"]={**(cat["games"][0].get("data_report") or {}),**report}
    p.write_text(json.dumps(cat,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (data/"catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(cat,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"repaired":len(repaired),"heroes_ranked_with_subsystems":ranked,"repaired_characters":repaired},ensure_ascii=False))
    if ranked < 528:
        missing=[e["canonical_name"] for e in cat.get("entities") or [] if not any(a.get("ranking_key")=="codex_analytical" and a.get("profile_key")=="optimized_subsystems" and a.get("tier_label")!="UNRANKED" for a in e.get("analysis",[]))]
        raise SystemExit("Unranked after fallback: "+json.dumps(missing,ensure_ascii=False))
if __name__=="__main__":main()
