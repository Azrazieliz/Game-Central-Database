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
    skill_repairs=0
    zero_effect_skills_before=0
    zero_effect_skills_after=0
    for e in cat.get("entities") or []:
        before=effect_count(e);changed=0
        for s in e.get("skills") or []:
            desc=s.get("description_source") or ""
            old=[ef for v in s.get("versions") or [] for ef in v.get("effects") or []]
            if desc and not old:
                zero_effect_skills_before += 1
            parsed=normalize_source_text(desc) if desc else []
            if parsed:
                if not s.get("versions"):s["versions"]=[{"effects":parsed}]
                else:s["versions"][0]["effects"]=parsed
                if len(parsed)!=len(old) or (not old and parsed):
                    changed += max(0,len(parsed)-len(old))
                    skill_repairs += 1
            if desc and not [ef for v in s.get("versions") or [] for ef in v.get("effects") or []]:
                zero_effect_skills_after += 1
        after=effect_count(e)
        if after!=before or changed:
            e["analysis_normalization_refresh"]={"source":"Kaisen Wiki skill text","reason":"Per-skill bilingual normalization refreshed before analytical ranking","effects_before":before,"effects_after":after}
            repaired.append({"entity_id":e["id"],"name":e["canonical_name"],"effects_before":before,"effects_after":after,"effects_added":after-before})
    cat["tier_lists"]=compute_rankings(cat.get("entities") or [],cat.get("subsystems") or [])
    cat["engine_version"]="0.7.3"
    ranked=sum(any(a.get("ranking_key")=="codex_analytical" and a.get("profile_key")=="optimized_subsystems" and a.get("tier_label")!="UNRANKED" for a in e.get("analysis",[])) for e in cat.get("entities") or [])
    report_path=root/"kaisen-system-enrichment-report.json"
    report=json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    report.update({"engine_version":"0.7.3","bilingual_skill_refresh_characters":repaired,"skills_reparsed":skill_repairs,"zero_effect_skills_before_refresh":zero_effect_skills_before,"zero_effect_skills_after_refresh":zero_effect_skills_after,"heroes_ranked_with_subsystems":ranked,"source_tiers_used_for_analysis":False})
    if cat.get("games"):
        cat["games"][0]["data_report"]={**(cat["games"][0].get("data_report") or {}),**report}
    p.write_text(json.dumps(cat,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (data/"catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(cat,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"repaired_characters":len(repaired),"skills_reparsed":skill_repairs,"zero_effect_skills_before":zero_effect_skills_before,"zero_effect_skills_after":zero_effect_skills_after,"heroes_ranked_with_subsystems":ranked,"repaired":repaired},ensure_ascii=False))
    if ranked < 528:
        missing=[e["canonical_name"] for e in cat.get("entities") or [] if not any(a.get("ranking_key")=="codex_analytical" and a.get("profile_key")=="optimized_subsystems" and a.get("tier_label")!="UNRANKED" for a in e.get("analysis",[]))]
        raise SystemExit("Unranked after fallback: "+json.dumps(missing,ensure_ascii=False))
if __name__=="__main__":main()
