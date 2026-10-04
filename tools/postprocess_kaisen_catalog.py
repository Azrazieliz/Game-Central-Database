#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from enrich_kaisen_systems import normalize_source_text, compute_rankings


BAD_DISPLAY_NAMES={"action failed","error","failed","undefined","null","unknown"}

def family_key(e):
    k=(e.get("entity_key") or "").split(":")[-1]
    k=re.sub(r"^herocard_","",k)
    return re.sub(r"\d+$","",k)

def latin_name(s):
    return bool(re.search(r"[A-Za-z]",s or "")) and not bool(re.search(r"[ぁ-んァ-ヶ一-龯]",s or ""))

def build_display_names(entities):
    groups={}
    for e in entities:groups.setdefault(family_key(e),[]).append(e)
    bases={}
    for k,rows in groups.items():
        candidates=[e.get("canonical_name","") for e in rows if latin_name(e.get("canonical_name","")) and e.get("canonical_name","").strip().lower() not in BAD_DISPLAY_NAMES and len(e.get("canonical_name",""))<42 and not re.search(r"[—·:&]",e.get("canonical_name",""))]
        if candidates:bases[k]=sorted(candidates,key=len)[0]
    fixed=[]
    for e in entities:
        raw=(e.get("canonical_name") or "").strip();base=bases.get(family_key(e));display=raw
        if raw.lower() in BAD_DISPLAY_NAMES and base:
            display=base
        elif raw and not latin_name(raw) and base:
            display=base
        if display!=raw:
            e["display_name"]=display
            e["display_name_source"]={"rule":"Kaisen identity family fallback","canonical_source_value":raw,"family_base":base}
            fixed.append({"entity_id":e["id"],"canonical_name":raw,"display_name":display})
    return fixed

def classify_skill_presentation(skill):
    effects=[ef for v in skill.get("versions") or [] for ef in v.get("effects") or []]
    desc=(skill.get("description_source") or "").strip()
    if effects:
        skill["presentation_class"]="gameplay"
        return "gameplay"
    mechanical=bool(re.search(r"%|damage|attack|hp|round|enemy|allies|increase|decrease|buff|debuff|heal|revive|shield|critical|ダメージ|攻撃|ＨＰ|HP|ターン|敵|味方|付与|回復|無効|上昇|低下",desc,re.I))
    if len(desc)>=120 and not mechanical:
        skill["presentation_class"]="source_note"
        skill["analysis_eligible"]=False
        return "source_note"
    skill["presentation_class"]="unparsed"
    skill["analysis_eligible"]=False
    return "unparsed"

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
    entities=cat.get("entities") or []
    display_name_fixes=build_display_names(entities)
    source_note_count=0
    unparsed_count=0
    for e in entities:
        for s in e.get("skills") or []:
            cls=classify_skill_presentation(s)
            source_note_count += 1 if cls=="source_note" else 0
            unparsed_count += 1 if cls=="unparsed" else 0
    cat["tier_lists"]=compute_rankings(entities,cat.get("subsystems") or [])
    cat.setdefault("analysis_policy",{}).update({"status":"experimental","user_facing_precision":"coarse","source_tier_inputs":False,"note":"Analytical tiers are a heuristic preview and are not displayed as authoritative card rankings."})
    cat["engine_version"]="0.8.0"
    ranked=sum(any(a.get("ranking_key")=="codex_analytical" and a.get("profile_key")=="optimized_subsystems" and a.get("tier_label")!="UNRANKED" for a in e.get("analysis",[])) for e in cat.get("entities") or [])
    report_path=root/"kaisen-system-enrichment-report.json"
    report=json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    report.update({"engine_version":"0.8.0","bilingual_skill_refresh_characters":repaired,"skills_reparsed":skill_repairs,"zero_effect_skills_before_refresh":zero_effect_skills_before,"zero_effect_skills_after_refresh":zero_effect_skills_after,"heroes_ranked_with_subsystems":ranked,"source_tiers_used_for_analysis":False,"display_name_fixes":display_name_fixes,"source_note_skills":source_note_count,"unparsed_skills":unparsed_count})
    if cat.get("games"):
        cat["games"][0]["data_report"]={**(cat["games"][0].get("data_report") or {}),**report}
    p.write_text(json.dumps(cat,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (data/"catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(cat,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"repaired_characters":len(repaired),"skills_reparsed":skill_repairs,"zero_effect_skills_before":zero_effect_skills_before,"zero_effect_skills_after":zero_effect_skills_after,"heroes_ranked_with_subsystems":ranked,"display_name_fixes":len(display_name_fixes),"source_note_skills":source_note_count,"unparsed_skills":unparsed_count,"repaired":repaired},ensure_ascii=False))
    if ranked < 528:
        missing=[e["canonical_name"] for e in cat.get("entities") or [] if not any(a.get("ranking_key")=="codex_analytical" and a.get("profile_key")=="optimized_subsystems" and a.get("tier_label")!="UNRANKED" for a in e.get("analysis",[]))]
        raise SystemExit("Unranked after fallback: "+json.dumps(missing,ensure_ascii=False))
if __name__=="__main__":main()
