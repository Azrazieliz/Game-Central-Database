#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sqlite3
from pathlib import Path

SCHEMA_VERSION=1

DDL="""
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE games(id INTEGER PRIMARY KEY,game_key TEXT UNIQUE,name TEXT,adapter_key TEXT,icon_path TEXT);
CREATE TABLE patches(id INTEGER PRIMARY KEY AUTOINCREMENT,game_id INTEGER,patch_key TEXT,version TEXT,title TEXT,released_at TEXT,payload_json TEXT,UNIQUE(game_id,patch_key));
CREATE TABLE sources(id INTEGER PRIMARY KEY AUTOINCREMENT,site_name TEXT,url TEXT,retrieved_at TEXT,game_version TEXT,patch_id INTEGER,conflict_status TEXT,UNIQUE(site_name,url,retrieved_at));
CREATE TABLE source_facts(id INTEGER PRIMARY KEY AUTOINCREMENT,source_id INTEGER,entity_id INTEGER,subsystem_type TEXT,subsystem_key TEXT,fact_type TEXT,fact_key TEXT,raw_value_json TEXT,normalized_value_json TEXT);

CREATE TABLE entities(id INTEGER PRIMARY KEY,game_id INTEGER NOT NULL,entity_key TEXT UNIQUE,canonical_name TEXT,display_name TEXT,rarity_key TEXT,faction_key TEXT,attribute_type TEXT,role_key TEXT,FOREIGN KEY(game_id) REFERENCES games(id));
CREATE TABLE aliases(entity_id INTEGER NOT NULL,alias TEXT NOT NULL,source TEXT,PRIMARY KEY(entity_id,alias),FOREIGN KEY(entity_id) REFERENCES entities(id));
CREATE TABLE images(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_id INTEGER,subsystem_type TEXT,subsystem_key TEXT,asset_type TEXT,display_role TEXT,pack_path TEXT,source_url TEXT,source_site TEXT,sha256 TEXT);
CREATE TABLE skills(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_id INTEGER NOT NULL,skill_key TEXT,name TEXT,skill_type TEXT,description_source TEXT,presentation_class TEXT,analysis_eligible INTEGER,FOREIGN KEY(entity_id) REFERENCES entities(id));
CREATE TABLE effects(id INTEGER PRIMARY KEY AUTOINCREMENT,skill_id INTEGER,entity_id INTEGER,subsystem_type TEXT,subsystem_key TEXT,effect_type TEXT,mechanic_key TEXT,polarity TEXT,target_json TEXT,magnitude_json TEXT,condition_json TEXT,timing_json TEXT,extension_json TEXT,FOREIGN KEY(skill_id) REFERENCES skills(id));
CREATE TABLE subsystems(subsystem_type TEXT NOT NULL,subsystem_key TEXT NOT NULL,name TEXT,section TEXT,source_url TEXT,compatibility_json TEXT,max_profile_json TEXT,source_data_json TEXT,PRIMARY KEY(subsystem_type,subsystem_key));
CREATE TABLE relationships(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_id INTEGER NOT NULL,relationship_type TEXT,name TEXT,payload_json TEXT,FOREIGN KEY(entity_id) REFERENCES entities(id));
CREATE TABLE provenance(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_id INTEGER,subsystem_type TEXT,subsystem_key TEXT,site_name TEXT,url TEXT,kind TEXT,retrieved_at TEXT,conflict_status TEXT);
CREATE TABLE compatibility(id INTEGER PRIMARY KEY AUTOINCREMENT,from_entity_id INTEGER,to_entity_id INTEGER,mode_key TEXT,direction TEXT,score REAL,evidence_json TEXT);
CREATE TABLE evaluations(entity_id INTEGER NOT NULL,mode_key TEXT NOT NULL,score REAL,grade TEXT,rank_order INTEGER,profile TEXT,confidence REAL,axes_json TEXT,loadout_json TEXT,PRIMARY KEY(entity_id,mode_key),FOREIGN KEY(entity_id) REFERENCES entities(id));
CREATE TABLE ranking_entries(mode_key TEXT NOT NULL,rank_order INTEGER NOT NULL,entity_id INTEGER NOT NULL,score REAL,grade TEXT,confidence REAL,PRIMARY KEY(mode_key,rank_order));
CREATE TABLE source_opinions(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_id INTEGER,site_name TEXT,kind TEXT,value_json TEXT,source_url TEXT,reference_only INTEGER NOT NULL DEFAULT 1);
CREATE TABLE roster_state(account_key TEXT NOT NULL DEFAULT 'local',entity_id INTEGER NOT NULL,owned INTEGER NOT NULL DEFAULT 0,investment_key TEXT,resources_json TEXT,updated_at TEXT,PRIMARY KEY(account_key,entity_id));
CREATE TABLE adapter_config(game_key TEXT PRIMARY KEY,config_json TEXT NOT NULL);
"""

def dumps(x):return json.dumps(x,ensure_ascii=False,separators=(",",":"))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);args=ap.parse_args()
    root=Path(args.out);cat=json.loads((root/"data/catalog.json").read_text(encoding="utf-8"))
    db=root/"game_codex.sqlite"
    if db.exists():db.unlink()
    con=sqlite3.connect(db);con.executescript(DDL);cur=con.cursor()
    meta={"schema_version":SCHEMA_VERSION,"engine_version":cat.get("engine_version"),"generated_at":cat.get("generated_at"),"analysis_status":(cat.get("analysis_policy") or {}).get("status")}
    cur.executemany("INSERT INTO metadata(key,value) VALUES (?,?)",[(k,str(v)) for k,v in meta.items() if v is not None])
    for g in cat.get("games") or []:
        cur.execute("INSERT INTO games(id,game_key,name,adapter_key,icon_path) VALUES (?,?,?,?,?)",(g.get("id"),g.get("game_key"),g.get("name"),g.get("adapter_key"),g.get("icon_path")))
    for pch in cat.get("patches") or []:
        cur.execute("INSERT OR IGNORE INTO patches(game_id,patch_key,version,title,released_at,payload_json) VALUES (?,?,?,?,?,?)",(pch.get("game_id"),pch.get("patch_key") or pch.get("version") or str(pch.get("id") or ""),pch.get("version"),pch.get("title") or pch.get("name"),pch.get("released_at") or pch.get("date"),dumps(pch)))
    adapter=cat.get("adapter") or {}
    if adapter:cur.execute("INSERT INTO adapter_config(game_key,config_json) VALUES (?,?)",(adapter.get("game_key") or "unknown",dumps(adapter)))
    for e in cat.get("entities") or []:
        cur.execute("INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?)",(e.get("id"),e.get("game_id"),e.get("entity_key"),e.get("canonical_name"),e.get("display_name") or e.get("canonical_name"),e.get("rarity_key"),e.get("faction_key"),e.get("attribute_type"),e.get("role_key")))
        for a in e.get("aliases") or []:
            if isinstance(a,dict):alias=a.get("alias") or a.get("name");src=a.get("source")
            else:alias=a;src=None
            if alias:cur.execute("INSERT OR IGNORE INTO aliases VALUES (?,?,?)",(e["id"],alias,src))
        for im in e.get("images") or []:
            cur.execute("INSERT INTO images(entity_id,asset_type,display_role,pack_path,source_url,source_site,sha256) VALUES (?,?,?,?,?,?,?)",(e["id"],im.get("asset_type"),im.get("display_role"),im.get("pack_path"),im.get("source_url"),im.get("source_site"),im.get("sha256")))
        entity_source_ids=[]
        for p in e.get("provenance") or []:
            cur.execute("INSERT INTO provenance(entity_id,site_name,url,kind,retrieved_at,conflict_status) VALUES (?,?,?,?,?,?)",(e["id"],p.get("site_name"),p.get("url"),p.get("kind") or p.get("fact_key"),p.get("retrieved_at"),p.get("conflict_status")))
            cur.execute("INSERT OR IGNORE INTO sources(site_name,url,retrieved_at,game_version,conflict_status) VALUES (?,?,?,?,?)",(p.get("site_name"),p.get("url"),p.get("retrieved_at"),p.get("game_version") or p.get("patch"),p.get("conflict_status")))
            sid=cur.execute("SELECT id FROM sources WHERE site_name IS ? AND url IS ? AND retrieved_at IS ?",(p.get("site_name"),p.get("url"),p.get("retrieved_at"))).fetchone()
            if sid:entity_source_ids.append(sid[0])
        for op in e.get("source_opinions") or []:
            cur.execute("INSERT INTO source_opinions(entity_id,site_name,kind,value_json,source_url,reference_only) VALUES (?,?,?,?,?,?)",(e["id"],op.get("site_name"),op.get("kind"),dumps(op.get("value") if "value" in op else op.get("tier_label")),op.get("source_url") or op.get("url"),1 if op.get("reference_only",True) else 0))
        for rel in e.get("relationships") or []:
            cur.execute("INSERT INTO relationships(entity_id,relationship_type,name,payload_json) VALUES (?,?,?,?)",(e["id"],rel.get("relationship_type"),rel.get("name"),dumps(rel)))
        for s in e.get("skills") or []:
            cur.execute("INSERT INTO skills(entity_id,skill_key,name,skill_type,description_source,presentation_class,analysis_eligible) VALUES (?,?,?,?,?,?,?)",(e["id"],s.get("skill_key"),s.get("name"),s.get("skill_type"),s.get("description_source"),s.get("presentation_class"),0 if s.get("analysis_eligible") is False else 1))
            sid=cur.lastrowid
            if entity_source_ids:
                cur.execute("INSERT INTO source_facts(source_id,entity_id,fact_type,fact_key,raw_value_json) VALUES (?,?,?,?,?)",(entity_source_ids[0],e["id"],"skill","description_source",dumps(s.get("description_source"))))
            for v in s.get("versions") or []:
                for ef in v.get("effects") or []:
                    cur.execute("INSERT INTO effects(skill_id,entity_id,effect_type,mechanic_key,polarity,target_json,magnitude_json,condition_json,timing_json,extension_json) VALUES (?,?,?,?,?,?,?,?,?,?)",(sid,e["id"],ef.get("effect_type"),ef.get("mechanic_key"),ef.get("polarity"),dumps(ef.get("target") or {}),dumps(ef.get("magnitude") or {}),dumps(ef.get("condition") or {}),dumps(ef.get("timing") or {}),dumps(ef.get("extension") or {})))
                    if entity_source_ids:
                        cur.execute("INSERT INTO source_facts(source_id,entity_id,fact_type,fact_key,raw_value_json,normalized_value_json) VALUES (?,?,?,?,?,?)",(entity_source_ids[0],e["id"],"normalized_effect",ef.get("mechanic_key") or ef.get("effect_type"),dumps((ef.get("extension") or {}).get("source_sentence")),dumps(ef)))
        ev=e.get("codex_evaluation") or {}
        for mode,row in (ev.get("scenarios") or {}).items():
            axes=row.get("optimized_axes") if row.get("profile")!="base" else (ev.get("axes") or {}).get("base")
            cur.execute("INSERT OR REPLACE INTO evaluations VALUES (?,?,?,?,?,?,?,?,?)",(e["id"],mode,row.get("score"),row.get("grade"),row.get("rank"),row.get("profile"),row.get("confidence"),dumps(axes or {}),dumps(row.get("selected_subsystems") or [])))
    for s in cat.get("subsystems") or []:
        cur.execute("INSERT INTO subsystems VALUES (?,?,?,?,?,?,?,?)",(s.get("subsystem_type"),s.get("subsystem_key"),s.get("name"),s.get("section"),s.get("source_url"),dumps(s.get("compatibility") or {}),dumps(s.get("max_profile") or {}),dumps(s.get("source_data") or {})))
        for im in s.get("images") or []:
            cur.execute("INSERT INTO images(subsystem_type,subsystem_key,asset_type,display_role,pack_path,source_url,source_site,sha256) VALUES (?,?,?,?,?,?,?,?)",(s.get("subsystem_type"),s.get("subsystem_key"),im.get("asset_type"),im.get("display_role"),im.get("pack_path"),im.get("source_url"),im.get("source_site"),im.get("sha256")))
        for p in s.get("provenance") or []:
            cur.execute("INSERT INTO provenance(subsystem_type,subsystem_key,site_name,url,kind,retrieved_at,conflict_status) VALUES (?,?,?,?,?,?,?)",(s.get("subsystem_type"),s.get("subsystem_key"),p.get("site_name"),p.get("url"),p.get("kind"),p.get("retrieved_at"),p.get("conflict_status")))
        for ef in (s.get("max_profile") or {}).get("effects") or []:
            cur.execute("INSERT INTO effects(subsystem_type,subsystem_key,effect_type,mechanic_key,polarity,target_json,magnitude_json,condition_json,timing_json,extension_json) VALUES (?,?,?,?,?,?,?,?,?,?)",(s.get("subsystem_type"),s.get("subsystem_key"),ef.get("effect_type"),ef.get("mechanic_key"),ef.get("polarity"),dumps(ef.get("target") or {}),dumps(ef.get("magnitude") or {}),dumps(ef.get("condition") or {}),dumps(ef.get("timing") or {}),dumps(ef.get("extension") or {})))
    for x in cat.get("compatibility") or []:
        cur.execute("INSERT INTO compatibility(from_entity_id,to_entity_id,mode_key,direction,score,evidence_json) VALUES (?,?,?,?,?,?)",(x.get("from_entity_id"),x.get("to_entity_id"),x.get("mode_key"),x.get("direction"),x.get("score"),dumps(x.get("evidence") or [])))
    for ranking in cat.get("rankings") or []:
        for x in ranking.get("entries") or []:
            cur.execute("INSERT INTO ranking_entries VALUES (?,?,?,?,?,?)",(ranking.get("mode_key"),x.get("rank"),x.get("entity_id"),x.get("score"),x.get("grade"),x.get("confidence")))
    con.commit();con.execute("VACUUM");con.close()

    csvdir=root/"csv";csvdir.mkdir(exist_ok=True)
    with (csvdir/"characters.csv").open("w",newline="",encoding="utf-8") as fh:
        w=csv.writer(fh);w.writerow(["id","entity_key","display_name","rarity","faction","attribute"])
        for e in cat.get("entities") or []:w.writerow([e.get("id"),e.get("entity_key"),e.get("display_name") or e.get("canonical_name"),e.get("rarity_key"),e.get("faction_key"),e.get("attribute_type")])
    with (csvdir/"rankings.csv").open("w",newline="",encoding="utf-8") as fh:
        w=csv.writer(fh);w.writerow(["mode","rank","entity_id","name","grade","score","confidence"])
        for ranking in cat.get("rankings") or []:
            for x in ranking.get("entries") or []:w.writerow([ranking.get("mode_key"),x.get("rank"),x.get("entity_id"),x.get("name"),x.get("grade"),x.get("score"),x.get("confidence")])
    with (csvdir/"subsystems.csv").open("w",newline="",encoding="utf-8") as fh:
        w=csv.writer(fh);w.writerow(["type","key","name","section","source_url"])
        for s in cat.get("subsystems") or []:w.writerow([s.get("subsystem_type"),s.get("subsystem_key"),s.get("name"),s.get("section"),s.get("source_url")])
    manifest={"schema_version":SCHEMA_VERSION,"engine_version":cat.get("engine_version"),"files":["data/catalog.json","data/catalog.js","game_codex.sqlite","csv/characters.csv","csv/rankings.csv","csv/subsystems.csv"],"asset_count":sum(len(e.get("images") or []) for e in cat.get("entities") or [])+sum(len(s.get("images") or []) for s in cat.get("subsystems") or [])}
    (root/"portable-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=="__main__":main()
