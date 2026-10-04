#!/usr/bin/env python3
from __future__ import annotations

import argparse, concurrent.futures, hashlib, html, io, json, re, time, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

BASE = "https://kaisen-wiki.h0rny.net"
UA = "GameCodex/0.5 (+https://github.com/Azrazieliz/Game-Central-Database)"
LISTS = {
    "heroes": "/heroes",
    "souls": "/souls",
    "martial_spirit": "/spirits",
    "mount": "/transcendent",
}
MODE_WEIGHTS = {
    "generic":{"damage":1.0,"survivability":1.0,"control":0.85,"utility":1.0,"counterplay":0.8,"reliability":1.0,"flexibility":0.9,"independence":0.8},
    "story":{"damage":1.0,"survivability":0.9,"control":0.8,"utility":1.0,"counterplay":0.6,"reliability":1.0,"flexibility":0.8,"independence":0.8},
    "pvp":{"damage":1.0,"survivability":1.05,"control":1.2,"utility":1.05,"counterplay":1.15,"reliability":1.0,"flexibility":1.0,"independence":0.8},
    "boss":{"damage":1.25,"survivability":1.0,"control":0.35,"utility":1.1,"counterplay":0.7,"reliability":1.0,"flexibility":0.75,"independence":0.8},
}
TIER_BANDS=((.97,"S+"),(.90,"S"),(.75,"A"),(.50,"B"),(.25,"C"),(0,"D"))
FEATURES=tuple(MODE_WEIGHTS["generic"])


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(s):
    s=html.unescape(str(s or ""))
    s=re.sub(r"<color=[^>]+>|</color>","",s,flags=re.I)
    return re.sub(r"\s+"," ",s).strip()


def kfetch_bytes(url, timeout=35, retries=3):
    if url.startswith("/"):
        url=BASE+url
    headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/json,image/avif,image/webp,image/*,*/*;q=0.8"}
    err=None
    for attempt in range(retries):
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return r.read(), r.headers.get("Content-Type","")
        except Exception as exc:
            err=exc
            time.sleep(0.35*(attempt+1))
    raise err


def kjson(path):
    raw,_=kfetch_bytes(path)
    return json.loads(raw.decode("utf-8")), raw


def save_raw(raw_dir, name, raw):
    p=raw_dir/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(raw)
    return str(p)


def asset_url(path):
    if not path:return None
    if path.startswith("http"):return path
    if path.startswith("/assets/"):return BASE+path
    return BASE+"/assets/"+path.lstrip("/")


def save_asset(url, out_dir, key, max_dim=1500):
    if not url:return None
    raw,_=kfetch_bytes(url,timeout=45)
    try:
        im=Image.open(io.BytesIO(raw));im.load()
        if im.width<48 or im.height<48:return None
        if max(im.size)>max_dim:
            sc=max_dim/max(im.size)
            im=im.resize((max(1,int(im.width*sc)),max(1,int(im.height*sc))),Image.Resampling.LANCZOS)
        if im.mode not in ("RGB","RGBA"):
            im=im.convert("RGBA" if "A" in im.mode else "RGB")
        name=hashlib.sha256((key+url).encode()).hexdigest()[:24]+".webp"
        p=out_dir/name
        im.save(p,"WEBP",quality=84,method=6)
        data=p.read_bytes()
        return {"pack_path":"assets/"+name,"sha256":hashlib.sha256(data).hexdigest(),"byte_size":len(data),"width":im.width,"height":im.height,"source_url":url}
    except Exception:
        ext=Path(urllib.parse.urlparse(url).path).suffix.lower() or ".bin"
        name=hashlib.sha256((key+url).encode()).hexdigest()[:24]+ext
        p=out_dir/name;p.write_bytes(raw)
        return {"pack_path":"assets/"+name,"sha256":hashlib.sha256(raw).hexdigest(),"byte_size":len(raw),"source_url":url}


def hero_key(entity):
    stem=entity.get("asset_stem") or entity.get("entity_key","").split(":")[-1]
    stem=Path(stem).stem
    return re.sub(r"^herocard_","",stem)


def source(site,url,kind,retrieved=None):
    return {"site_name":site,"url":url,"kind":kind,"retrieved_at":retrieved or now(),"conflict_status":"none"}


def target_from_text(s):
    l=s.lower()
    if "all enemies" in l:return {"side":"enemy","scope":"all"}
    m=re.search(r"(?:the\s+)?(\d+)\s+enemies",l)
    if m:return {"side":"enemy","count":int(m.group(1))}
    if "random enem" in l:return {"side":"enemy","scope":"random"}
    if "enemy" in l:return {"side":"enemy","count":1}
    if "all allies" in l or "all friendly" in l:return {"side":"ally","scope":"all"}
    m=re.search(r"(?:the\s+)?(\d+)\s+(?:allies|friendly)",l)
    if m:return {"side":"ally","count":int(m.group(1))}
    if any(x in l for x in ("yourself","self","this hero")):return {"side":"self","count":1}
    return {}


def base_effect(sentence, etype, mechanic, polarity=None, magnitude=None, extension=None):
    s=clean(sentence);l=s.lower()
    dur=None
    m=re.search(r"(?:for|lasts? for|lasting)\s+(\d+)\s+round",l)
    if m:dur=int(m.group(1))
    cond={}
    if re.search(r"\b(if|when|while|each time|at the start|after|before)\b",l):cond["conditional"]=True
    hp=re.search(r"hp[^.%]{0,18}(\d+(?:\.\d+)?)%\s*(?:or less|below|under)",l)
    if hp:cond["hp_lte_percent"]=float(hp.group(1))
    timing={}
    if dur is not None:timing["duration_rounds"]=dur
    if "start of each round" in l or "start of the round" in l:timing["trigger"]="round_start"
    if "after entering the field" in l:timing["trigger"]="on_enter"
    if "each time this hero acts" in l:timing["trigger"]="on_action"
    return {"effect_type":etype,"mechanic_key":mechanic,"polarity":polarity,"target":target_from_text(s),"magnitude":magnitude or {},"condition":cond,"timing":timing,"extension":{"source_sentence":s,**(extension or {})}}


STAT_PATTERNS={
 "attack_up":[r"attack(?: power)?(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"attack(?: power)?\s*\+\s*(\d+(?:\.\d+)?)%"],
 "defense_up":[r"defen[cs]e(?: power)?(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"defen[cs]e(?: power)?\s*\+\s*(\d+(?:\.\d+)?)%"],
 "crit_rate_up":[r"(?:critical hit|crit(?:ical)?)(?: rate)?(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"(?:critical hit|crit(?:ical)?) rate\s*\+\s*(\d+(?:\.\d+)?)%"],
 "crit_damage_up":[r"(?:critical (?:hit|strike) damage|crit(?:ical)? dmg)(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"(?:critical (?:hit|strike) damage|crit(?:ical)? dmg)\s*\+\s*(\d+(?:\.\d+)?)%"],
 "hit_rate_up":[r"(?<!critical )(?<!crit )hit rate(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"(?<!critical )(?<!crit )hit rate\s*\+\s*(\d+(?:\.\d+)?)%"],
 "block_rate_up":[r"block(?:ing)? rate(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"block(?:ing)? rate\s*\+\s*(\d+(?:\.\d+)?)%"],
 "dodge_up":[r"dodge(?: rate)?(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"dodge(?: rate)?\s*\+\s*(\d+(?:\.\d+)?)%"],
 "status_resist_up":[r"abnormal state tolerance(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%"],
 "lifesteal_up":[r"hp absorption(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%"],
 "penetration_up":[r"(?:armor|protection) penetration(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"(?:armor|protection) penetration\s*\+\s*(\d+(?:\.\d+)?)%"],
 "damage_up":[r"(?<!taken )(?<!received )damage(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"damage\s*\+\s*(\d+(?:\.\d+)?)%"],
 "damage_reduction":[r"damage (?:taken|received)(?: is)? (?:reduced|decreased) by\s*(\d+(?:\.\d+)?)%",r"damage reduction\s*\+\s*(\d+(?:\.\d+)?)%"],
 "hp_up":[r"(?:max )?hp(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%",r"(?:max )?hp\s*\+\s*(\d+(?:\.\d+)?)%"],
 "physical_resist_up":[r"(?:physical|p-)resist(?:ance)?(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%"],
 "magic_resist_up":[r"(?:magic|m-)resist(?:ance)?(?: is)? (?:increased|increase(?:s)?) by\s*([+-]?\d+(?:\.\d+)?)%"],
}


def normalize_english(text):
    raw=clean(text);out=[]
    parts=[clean(x) for x in re.split(r"(?<=[.!?])\s+|\n+|;\s*",raw) if clean(x)]
    for s in parts:
        sl=s.lower()
        hits=1
        for hp in (r"conduct\s+(\d+)\s+attacks",r"deal\s+(\d+)\s+damage\s+to",r"(\d+)\s+attacks"):
            m=re.search(hp,sl)
            if m:hits=max(hits,int(m.group(1)))
        for m in re.finditer(r"([\d,]+(?:\.\d+)?)%\s*(physical|magic|real|true) damage",sl):
            val=float(m.group(1).replace(",",""));typ=m.group(2)
            mech={"physical":"physical_damage","magic":"magic_damage","real":"true_damage","true":"true_damage"}[typ]
            out.append(base_effect(s,"damage",mech,"negative",{"percent":val,"percent_values":[val],"hits":hits},{"damage_type":typ}))
        for pat in (r"restore(?:s)?\s+(\d+(?:\.\d+)?)%\s+of (?:your|its|their|the target'?s?)?\s*hp",r"recovers?\s+(\d+(?:\.\d+)?)%\s+hp",r"heal(?:s|ing)?[^.]{0,30}?(\d+(?:\.\d+)?)%"):
            m=re.search(pat,sl)
            if m:
                v=float(m.group(1));out.append(base_effect(s,"heal","healing","positive",{"percent":v,"percent_values":[v]}));break
        if "revive" in sl or "resurrect" in sl:out.append(base_effect(s,"revive","revive","positive"))
        if "hp will not drop below 1" in sl or "hp cannot drop below 1" in sl:out.append(base_effect(s,"immunity","death_prevention","positive"))
        if "shield" in sl:out.append(base_effect(s,"shield","shield","positive"))
        if ("clear" in sl or "remove" in sl or "dispel" in sl) and ("strengthening effect" in sl or "buff" in sl):out.append(base_effect(s,"dispel","buff","negative"))
        if ("clear" in sl or "remove" in sl or "cleanse" in sl) and ("abnormal state" in sl or "debuff" in sl):out.append(base_effect(s,"cleanse","status_effect","positive"))
        if "must hit" in sl or "attacks always hit" in sl:out.append(base_effect(s,"buff","guaranteed_hit","positive",{"boolean":True}))
        if "critical hits must occur" in sl or "guaranteed critical" in sl:out.append(base_effect(s,"buff","guaranteed_crit","positive",{"boolean":True}))
        if "ignore defense" in sl or "ignoring defense" in sl:out.append(base_effect(s,"counter","defense_ignore","positive",{"boolean":True}))
        if "ignore protection" in sl or "ignoring protection" in sl:out.append(base_effect(s,"counter","protection_ignore","positive",{"boolean":True}))
        stat_labels={
            "attack_up":r"attack(?: power)?","defense_up":r"defen[cs]e(?: power)?",
            "crit_rate_up":r"(?:critical hit|crit(?:ical)?)(?: rate)?",
            "crit_damage_up":r"(?:critical (?:hit|strike) damage|crit(?:ical)? dmg)",
            "hit_rate_up":r"(?<!critical )(?<!crit )hit rate","block_rate_up":r"block(?:ing)? rate",
            "dodge_up":r"dodge(?: rate)?","status_resist_up":r"abnormal state tolerance",
            "lifesteal_up":r"hp absorption","penetration_up":r"(?:armor|protection) penetration",
            "damage_up":r"damage","damage_reduction":r"damage (?:taken|received)|damage reduction",
            "hp_up":r"(?:max )?hp","physical_resist_up":r"(?:physical|p-)resist(?:ance)?",
            "magic_resist_up":r"(?:magic|m-)resist(?:ance)?"}
        for mech,pats in STAT_PATTERNS.items():
            vals=[]
            for pat in pats:vals += [float(x) for x in re.findall(pat,sl)]
            label=stat_labels.get(mech)
            if label:
                vals += [float(x) for x in re.findall(rf"increases?\s+(?:{label})\s+by\s*([+-]?\d+(?:\.\d+)?)%",sl) if x not in ("", None)]
            if vals:out.append(base_effect(s,"buff",mech,"positive",{"percent":max(vals),"percent_values":vals}))
        m=re.search(r"enemy[^.]{0,80}?deal\s*-\s*(\d+(?:\.\d+)?)%",sl)
        if m:
            v=float(m.group(1));out.append(base_effect(s,"debuff","enemy_damage_down","negative",{"percent":v,"percent_values":[v]}))
        if any(x in sl for x in ("cannot recover hp","healing is invalid","unable to recover hp")):out.append(base_effect(s,"debuff","heal_block","negative"))
        for m in re.finditer(r"normal attack dmg\s*[x×]\s*(\d+(?:\.\d+)?)",sl):
            out.append(base_effect(s,"buff","normal_attack_multiplier","positive",{"multiplier":float(m.group(1))}))
        for label,mech in (("max hp","hp_flat_per_level"),("hp","hp_flat_per_level"),("attack","attack_flat_per_level"),("defense","defense_flat_per_level")):
            m=re.search(rf"{label}\s*\+\s*lv\s*\*\s*([\d,.]+)",sl)
            if m:out.append(base_effect(s,"stat_flat",mech,"positive",{"per_level":float(m.group(1).replace(",",""))},{"excluded_from_percentage_scaling":True}))
        names=re.findall(r"['\"]([^'\"]{2,45})['\"]\s*state",s,flags=re.I)
        for name in dict.fromkeys(clean(x) for x in names):
            if name:out.append(base_effect(s,"extension","status:"+re.sub(r"[^a-z0-9]+","_",name.lower()).strip("_"),None,{},{"source_status_name":name}))
    ded=[];seen=set()
    for e in out:
        key=(e["effect_type"],e["mechanic_key"],json.dumps(e.get("target",{}),sort_keys=True),json.dumps(e.get("magnitude",{}),sort_keys=True),e["extension"].get("source_sentence"))
        if key not in seen:seen.add(key);ded.append(e)
    return ded


def target_from_japanese(s):
    if any(x in s for x in ("敵全体","全敵武将","全ての敵武将")):return {"side":"enemy","scope":"all"}
    m=re.search(r"敵(?:武将)?(\d+)人",s)
    if m:return {"side":"enemy","count":int(m.group(1))}
    if "ランダムな敵" in s:return {"side":"enemy","scope":"random"}
    if any(x in s for x in ("味方全体","味方武将全体","全味方武将")):return {"side":"ally","scope":"all"}
    m=re.search(r"味方(?:武将)?(\d+)人",s)
    if m:return {"side":"ally","count":int(m.group(1))}
    if any(x in s for x in ("自身","自分")):return {"side":"self","count":1}
    return {}


def jp_effect(sentence,etype,mechanic,polarity=None):
    vals=[float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*[%％]",sentence)]
    hits=None
    for pat in (r"(\d+)回(?:攻撃|ダメージ)",r"敵に(\d+)回"):
        m=re.search(pat,sentence)
        if m:hits=int(m.group(1));break
    dur=re.search(r"(\d+)ターン",sentence)
    cond={}
    if any(x in sentence for x in ("場合","時","たびに","前","後")):cond["conditional"]=True
    mag={"percent_values":vals}
    if hits:mag["hits"]=hits
    return {"effect_type":etype,"mechanic_key":mechanic,"polarity":polarity,"target":target_from_japanese(sentence),"magnitude":mag,"condition":cond,"timing":{"duration_rounds":int(dur.group(1))} if dur else {},"extension":{"source_sentence":clean(sentence),"source_language":"ja"}}


def normalize_japanese(text):
    out=[]
    sentences=[clean(x) for x in re.split(r"(?<=[。！？])|\n+",clean(text)) if clean(x)]
    for s in sentences:
        if "ダメージ" in s:
            mech="piercing_damage" if "貫通ダメージ" in s else ("physical_damage" if "物理ダメージ" in s else ("magic_damage" if "法術ダメージ" in s else "damage"))
            out.append(jp_effect(s,"damage",mech,"negative"))
        if re.search(r"(?:HP[^。]{0,35}?回復|HPを[^。]{0,25}?回復|回復して復活|HPを回復)",s) and not any(x in s for x in ("回復不可","回復できない","HP回復不可")):
            out.append(jp_effect(s,"heal","healing","positive"))
        if "復活" in s:
            out.append(jp_effect(s,"revive","revive","positive"))
        if "強化効果" in s and any(x in s for x in ("消去","解除","奪い取","減ら")):
            out.append(jp_effect(s,"dispel","buff","negative"))
        if "状態異常" in s and any(x in s for x in ("消去","解除","残りターン数-")):
            out.append(jp_effect(s,"cleanse","status_effect","positive"))
        if any(x in s for x in ("戦闘不能になるダメージ無効","HPが1以下にならない","HPは1以下にならない")):
            out.append(jp_effect(s,"immunity","death_prevention","positive"))
        if "ダメージ無効化" in s and "無視" not in s:
            out.append(jp_effect(s,"immunity","damage_immunity","positive"))
        if any(x in s for x in ("回復不可","HP回復不可","HPを回復できない")):
            out.append(jp_effect(s,"debuff","heal_block","negative"))
        checks=[
          (r"攻撃力[^。]{0,24}(?:\+|上昇)", "buff","attack_up","positive"),
          (r"攻撃力[^。]{0,24}(?:-|低下)", "debuff","attack_down","negative"),
          (r"防御力[^。]{0,24}(?:\+|上昇)", "buff","defense_up","positive"),
          (r"防御力[^。]{0,24}(?:-|低下)", "debuff","defense_down","negative"),
          (r"(?<!被)ダメージ[^。]{0,18}(?:\+|上昇)", "buff","damage_up","positive"),
          (r"被ダメージ[^。]{0,24}(?:-|低下)", "buff","damage_reduction","positive"),
          (r"被ダメージ[^。]{0,24}(?:\+|上昇)", "debuff","damage_taken_up","negative"),
          (r"会心率[^。]{0,18}(?:\+|上昇)", "buff","crit_rate_up","positive"),
          (r"会心ダメージ[^。]{0,18}(?:\+|上昇)", "buff","crit_damage_up","positive"),
          (r"命中率[^。]{0,18}(?:\+|上昇)", "buff","hit_rate_up","positive"),
          (r"回避率?[^。]{0,18}(?:\+|上昇)", "buff","dodge_up","positive"),
          (r"ブロック率?[^。]{0,18}(?:\+|上昇)", "buff","block_rate_up","positive"),
          (r"(?:防御貫通|防護貫通|徹甲)[^。]{0,18}(?:\+|上昇)", "buff","penetration_up","positive"),
          (r"HP吸収[^。]{0,18}(?:\+|上昇)", "buff","lifesteal_up","positive"),
          (r"状態異常耐性[^。]{0,18}(?:\+|上昇)", "buff","status_resist_up","positive"),
          (r"HP上限[^。]{0,18}(?:\+|上昇)", "buff","hp_up","positive"),
        ]
        for pat,et,mk,pol in checks:
            if re.search(pat,s):out.append(jp_effect(s,et,mk,pol))
        if "シールド" in s or re.search(r"[聖魔魂]甲",s):
            out.append(jp_effect(s,"shield","shield","positive"))
        if "落桜" in s:
            if any(x in s for x in ("付与","獲得","回復する")):out.append(jp_effect(s,"resource_generate","sakura_petals","positive"))
            if any(x in s for x in ("失う","奪い取","消去","減少")):out.append(jp_effect(s,"resource_consume","sakura_petals","negative"))
        if "追加" in s and "スキル" in s and "発動" in s:
            out.append(jp_effect(s,"trigger","extra_skill_cast","positive"))
        if "無視" in s and any(x in s for x in ("ダメージ無効","防御","防護","被会心ダメージ低下")):
            out.append(jp_effect(s,"counter","defensive_immunity","positive"))
        if "会心" in s and any(x in s for x in ("発動しない","発動不可","会心になら")):
            out.append(jp_effect(s,"debuff","crit_disable","negative"))
    ded=[];seen=set()
    for e in out:
        key=(e["effect_type"],e["mechanic_key"],json.dumps(e.get("target",{}),sort_keys=True),e["extension"].get("source_sentence"))
        if key not in seen:seen.add(key);ded.append(e)
    return ded


def normalize_source_text(text):
    raw=clean(text)
    effects=list(normalize_english(raw))
    # Kaisen skill text can be mixed: English stat passives plus Japanese active/passive
    # mechanics on the same hero.  Japanese normalization must therefore run whenever
    # Japanese is present, not only when the English parser returned nothing.
    if re.search(r"[ぁ-んァ-ヶ一-龯]",raw):
        effects.extend(normalize_japanese(raw))
    ded=[];seen=set()
    for e in effects:
        key=(e.get("effect_type"),e.get("mechanic_key"),json.dumps(e.get("target") or {},sort_keys=True),json.dumps(e.get("magnitude") or {},sort_keys=True),json.dumps(e.get("condition") or {},sort_keys=True),clean((e.get("extension") or {}).get("source_sentence")))
        if key not in seen:
            seen.add(key);ded.append(e)
    return ded


def skill_type_from_api(skill):
    return {1:"normal",2:"active",3:"passive",4:"passive"}.get(skill.get("type"),"skill")


def api_skills(detail):
    meta=detail.get("meta") or {};rows=[];source_rows=[]
    for key in ("skills","weddingSkills"):
        vals=meta.get(key) or []
        if isinstance(vals,dict):vals=list(vals.values())
        if isinstance(vals,list):source_rows += [x for x in vals if isinstance(x,dict)]
    for key in ("manifestSkill","mhSkill","divineSkill"):
        v=meta.get(key)
        if isinstance(v,dict):source_rows.append(v)
        elif isinstance(v,list):source_rows += [x for x in v if isinstance(x,dict)]
    seen=set()
    for i,s in enumerate(source_rows):
        desc=clean(s.get("desc") or s.get("detailDesc"));name=clean(s.get("name") or f"Skill {i+1}")
        if not desc:continue
        sig=(s.get("id"),name,desc)
        if sig in seen:continue
        seen.add(sig)
        rows.append({"skill_key":"kaisen:"+str(s.get("id") or i),"name":name,"skill_type":skill_type_from_api(s),"description_source":desc,"source_site":"Kaisen Wiki","source_skill_id":s.get("id"),"versions":[{"effects":normalize_source_text(desc)}]})
    return rows


def parse_soul_list(text):
    soup=BeautifulSoup(text,"html.parser");sets=[];variants=defaultdict(list)
    for b in soup.select("button.soul-cell"):
        img=b.find("img");src=(img.get("src") if img else "") or "";title=clean(b.get("title"))
        m=re.search(r"/souls/([^/.]+)\.webp",src)
        if not m:continue
        key=m.group(1);base=re.sub(r"_event_.*$","",key);event=key[len(base)+7:] if "_event_" in key else None
        variants[base].append({"variant_key":key,"label":title,"event_label":event,"source_image":BASE+src})
        if "soul-cell-default" in (b.get("class") or []):sets.append({"key":base,"name":title,"source_image":BASE+src})
    return sets,dict(variants)


def parse_spirit_list(text):
    soup=BeautifulSoup(text,"html.parser");out=[]
    for b in soup.select("button.spirit-cell"):
        img=b.find("img");src=(img.get("src") if img else "") or "";name=clean(b.get("title"))
        m=re.search(r"weaponcard_(.+?)_(shen|xian|mo|ren)02\.webp",src)
        if m:out.append({"key":m.group(1),"element":m.group(2),"name":name,"source_image":BASE+src})
    return out


def parse_mount_list(text):
    soup=BeautifulSoup(text,"html.parser");out=[]
    for b in soup.select("button.mount-cell"):
        img=b.find("img");src=(img.get("src") if img else "") or "";name=clean(b.get("title"))
        m=re.search(r"mountcard_(.+?)\.webp",src)
        if m:out.append({"key":m.group(1),"name":name,"source_image":BASE+src})
    return out


def progression_effects(desc):return normalize_english(desc or "")


def subsystem_record(kind, entry, detail, variants=None, image_meta=None, attr_map=None):
    api_url=f"{BASE}/api/album/{detail.get('id')}"
    rec={"subsystem_type":kind,"subsystem_key":entry["key"],"name":detail.get("displayName") or entry.get("name"),"section":detail.get("section"),"source_url":api_url,"images":[],"progression":[],"max_profile":{},"compatibility":{},"provenance":[source("Kaisen Wiki",api_url,f"subsystem.{kind}")],"source_data":{}}
    if image_meta:rec["images"].append({"asset_type":"card","display_role":"grid_card","priority":100,**image_meta})
    if kind=="soul":
        d=detail.get("soul") or {};skills=d.get("skills") or [];maxskill=max(skills,key=lambda x:x.get("tier",-1)) if skills else None
        rec["category"]="limited" if d.get("limited") else "standard";rec["profession_fit"]=d.get("professionFit") or []
        rec["compatibility"]={"type":"profession","professions":rec["profession_fit"]}
        rec["variants"]=variants or d.get("variants") or []
        rec["source_data"]={"set_id":d.get("setId"),"description":d.get("desc"),"auto_recycle":d.get("autoRecycle")}
        for s in skills:rec["progression"].append({"level":s.get("tier"),"quality":s.get("qualityLabel"),"name":s.get("name"),"description":clean(s.get("desc")),"effects":progression_effects(s.get("desc"))})
        bonus_effects=[]
        for b in d.get("bonuses") or []:bonus_effects += progression_effects(clean(b.get("desc")))
        maxeff=(progression_effects(maxskill.get("desc")) if maxskill else [])+bonus_effects
        if d.get("stars5Skill") and isinstance(d["stars5Skill"],dict):maxeff+=progression_effects(d["stars5Skill"].get("desc"))
        rec["max_profile"]={"level":maxskill.get("tier") if maxskill else None,"description":clean(maxskill.get("desc")) if maxskill else None,"effects":maxeff,"set_bonuses":d.get("bonuses") or []}
    elif kind=="martial_spirit":
        d=detail.get("spirit") or {};skills=d.get("skills") or [];maxskill=max(skills,key=lambda x:x.get("level",-1)) if skills else None
        rec["element"]=detail.get("spiritType") or entry.get("element");rec["source_data"]={"template_id":d.get("templateId"),"cv":d.get("cv"),"launch_time":d.get("launchTime"),"six_star_attr_raw":d.get("sixStarAttr")}
        heroes=d.get("compatibleHeroes") or []
        rec["compatibility"]={"type":"explicit_heroes","hero_keys":[h.get("charName") for h in heroes if h.get("charName")],"heroes":heroes}
        for s in skills:rec["progression"].append({"level":s.get("level"),"name":s.get("name"),"description":clean(s.get("desc")),"effects":progression_effects(s.get("desc"))})
        effects=progression_effects(maxskill.get("desc")) if maxskill else []
        raw=d.get("sixStarAttr")
        if raw:
            m=re.match(r"\d+_(\d+)_([\d.]+)$",str(raw));stat={"raw":raw}
            if m:
                aid=int(m.group(1));val=float(m.group(2));stat.update({"attr_id":aid,"value":val,"attr":(attr_map or {}).get(aid)})
                effects.append({"effect_type":"stat_flat","mechanic_key":"martial_spirit_six_star_attr","polarity":"positive","target":{"side":"self"},"magnitude":{"flat":val},"condition":{},"timing":{},"extension":{"attr_id":aid,"attr":(attr_map or {}).get(aid),"raw":raw,"excluded_from_percentage_scaling":True}})
            rec["source_data"]["six_star_attr"]=stat
        rec["max_profile"]={"level":maxskill.get("level") if maxskill else None,"description":clean(maxskill.get("desc")) if maxskill else None,"effects":effects}
    elif kind=="mount":
        d=detail.get("transcendent") or {};skills=d.get("skills") or [];maxskill=max(skills,key=lambda x:x.get("level",-1)) if skills else None
        rec["source_data"]={"template_id":d.get("templateId"),"cv":d.get("cv"),"launch_time":d.get("launchTime")}
        rec["compatibility"]={"type":"all_heroes_by_current_game_rule","source_constraint":None,"assumption":"Kaisen Wiki mount detail exposes no per-character compatibility restriction; optimized-ceiling analysis treats the mount as universally equipable."}
        for s in skills:rec["progression"].append({"level":s.get("level"),"name":s.get("name"),"description":clean(s.get("desc")),"effects":progression_effects(s.get("desc"))})
        rec["max_profile"]={"level":maxskill.get("level") if maxskill else None,"description":clean(maxskill.get("desc")) if maxskill else None,"effects":progression_effects(maxskill.get("desc")) if maxskill else []}
    return rec


def flatten_effects_from_skills(skills):return [ef for s in skills for v in s.get("versions",[]) for ef in v.get("effects",[])]


def all_effects(entity, extras=None):
    out=flatten_effects_from_skills(entity.get("skills",[]))
    for x in extras or []:out += (x.get("max_profile") or {}).get("effects") or []
    return out


def pct(e):
    m=e.get("magnitude") or {}
    if "percent" in m:return float(m["percent"])
    return max([float(x) for x in (m.get("percent_values") or [])],default=0.0)


def breadth(e):
    t=e.get("target") or {}
    if t.get("scope") in ("all","random"):return 6.0
    return float(t.get("count") or 1)


def feature_vector(entity, extras=None):
    effects=all_effects(entity,extras);v={k:0.0 for k in FEATURES};families=set();uncond=0
    direct_damage=0.0;atk=0;dmg=0;crit=0;critd=0;pen=0;normal_mult=1.0
    hp=defn=block=red=life=0;reliable=0
    for e in effects:
        et=e.get("effect_type");mk=e.get("mechanic_key");p=pct(e);b=breadth(e);m=e.get("magnitude") or {}
        conditional=bool(e.get("condition"));uncond += 0 if conditional else 1
        if et=="damage":
            direct_damage += p*float(m.get("hits") or 1)*b*(1.12 if mk=="true_damage" else 1);families.add("damage")
        if mk=="attack_up":atk+=p
        elif mk=="damage_up":dmg+=p
        elif mk=="crit_rate_up":crit+=p
        elif mk=="crit_damage_up":critd+=p
        elif mk=="penetration_up":pen+=p
        elif mk=="normal_attack_multiplier":normal_mult=max(normal_mult,float(m.get("multiplier") or 1))
        elif mk=="hp_up":hp+=p
        elif mk=="defense_up":defn+=p
        elif mk=="block_rate_up":block+=p
        elif mk=="damage_reduction":red+=p
        elif mk=="lifesteal_up":life+=p
        elif mk in ("hit_rate_up","guaranteed_hit"):reliable += 1+p/100
        elif mk=="guaranteed_crit":reliable += 1.5
        if et in ("heal","shield"):v["survivability"]+=1.2+p/100;families.add("sustain")
        if et=="revive":v["survivability"]+=3.0;families.add("sustain")
        if et=="immunity":v["survivability"]+=2.0;v["counterplay"]+=0.7;families.add("sustain")
        if et=="cleanse":v["utility"]+=1.4;v["counterplay"]+=1.0;families.add("support")
        if et=="dispel":v["utility"]+=1.0;v["counterplay"]+=1.4;families.add("counter")
        if et=="debuff":v["control"]+=1.0+p/200;v["utility"]+=0.4;families.add("control")
        if et=="counter":v["counterplay"]+=1.25;families.add("counter")
        if et=="buff":v["utility"]+=0.35;families.add("support")
        if et=="extension":families.add("extension")
    damage_mult=(1+atk/100)*(1+dmg/100)*(1+min(crit,150)/100*min(critd,400)/100*0.25)*(1+min(pen,200)/100*0.25)
    v["damage"]=direct_damage*damage_mult + max(0,normal_mult-1)*600
    v["survivability"] += hp/12 + defn/15 + block/12 + red/10 + life/18
    v["reliability"] = reliable + (uncond/max(1,len(effects)))
    v["flexibility"] = float(len(families))
    v["independence"] = uncond/max(1,len(effects)) if effects else 0
    return v


def percentile_map(values):
    if not values:return {}
    ids=list(values);vals=list(values.values());n=len(vals)
    if n==1:return {ids[0]:1.0}
    out={}
    for i,x in values.items():
        less=sum(v<x for v in vals);eq=sum(v==x for v in vals)
        out[i]=(less+(eq-1)/2)/(n-1)
    return out


def percentile_value(sorted_vals,x):
    import bisect
    if not sorted_vals:return 0.0
    if len(sorted_vals)==1:return 1.0
    left=bisect.bisect_left(sorted_vals,x);right=bisect.bisect_right(sorted_vals,x)
    return min(1.0,max(0.0,(left+(right-left-1)/2)/(len(sorted_vals)-1)))


def tier(p):
    for threshold,label in TIER_BANDS:
        if p>=threshold:return label
    return "D"


def hero_professions(e):return set((e.get("kaisen_meta") or {}).get("professions") or [])
def compatible_souls(e,subs):
    hp=hero_professions(e)
    return [s for s in subs if s["subsystem_type"]=="soul" and (not s.get("profession_fit") or hp.intersection(s.get("profession_fit") or []))]
def compatible_spirits(e,subs):
    hk=hero_key(e)
    return [s for s in subs if s["subsystem_type"]=="martial_spirit" and hk in set((s.get("compatibility") or {}).get("hero_keys") or [])]
def compatible_mounts(e,subs):return [s for s in subs if s["subsystem_type"]=="mount"]


def compute_rankings(entities,subs):
    eligible=[e for e in entities if len(e.get("skills",[]))>=1 and len(flatten_effects_from_skills(e.get("skills",[])))>=1]
    base_raw={e["id"]:feature_vector(e) for e in eligible}
    base_sorted={f:sorted(base_raw[i][f] for i in base_raw) for f in FEATURES}
    result_lists=[]
    for e in entities:
        e["analysis"]=[a for a in e.get("analysis",[]) if a.get("ranking_key") not in (None,"codex_analytical") and not str(a.get("title","")).startswith("Codex analytical tier")]
    for mode,weights in MODE_WEIGHTS.items():
        chosen={};optimized_raw={}
        for e in eligible:
            # Transparent slot-wise optimization.  Exhaustive Soul × Spirit × Mount
            # search grows unnecessarily large; instead each slot is added in a fixed
            # documented order and accepted only when it improves the same mode score.
            selected=[];evaluated=0
            def score_vec(vec):
                return sum(weights[f]*percentile_value(base_sorted[f],vec[f]) for f in FEATURES)/sum(weights.values())
            current_vec=feature_vector(e,selected);current_score=score_vec(current_vec)
            for slot_options in (compatible_souls(e,subs),compatible_spirits(e,subs),compatible_mounts(e,subs)):
                slot_best=(current_score,None,current_vec)
                for candidate in slot_options:
                    vec=feature_vector(e,selected+[candidate]);evaluated+=1;score=score_vec(vec)
                    if score>slot_best[0]:slot_best=(score,candidate,vec)
                if slot_best[1] is not None:
                    selected.append(slot_best[1]);current_score=slot_best[0];current_vec=slot_best[2]
            chosen[e["id"]]={"selection_score_vs_base_population":round(current_score*100,3),"subsystems":[{"type":x["subsystem_type"],"key":x["subsystem_key"],"name":x["name"],"compatibility":x.get("compatibility")} for x in selected],"candidates_evaluated":evaluated,"optimization_order":["soul","martial_spirit","mount"]}
            optimized_raw[e["id"]]=current_vec
        for profile,raws in (("base",base_raw),("optimized_subsystems",optimized_raw)):
            norms={f:percentile_map({eid:vec[f] for eid,vec in raws.items()}) for f in FEATURES}
            scored=[]
            for e in eligible:
                eid=e["id"];factors={};score=0;ws=sum(weights.values())
                for f,w in weights.items():
                    p=norms[f][eid];score+=p*w
                    factors[f]={"raw":round(raws[eid][f],5),"population_score":round(p,6),"weight":w,"weighted_contribution":round(p*w,6)}
                scored.append((100*score/ws,e,factors))
            scored.sort(key=lambda x:(-x[0],x[1]["id"]));n=len(scored);rows=[]
            for pos,(score,e,factors) in enumerate(scored,1):
                p=1-(pos-1)/(n-1) if n>1 else 1;loadout=chosen[e["id"]] if profile=="optimized_subsystems" else None
                evidence={"formula_version":"kaisen-system-scaling-v1","source_tiers_used":False,"profile":profile,"loadout":loadout,"scaling_notes":["Percent/stat effects are parsed from sourced kit/subsystem descriptions.","Flat +Lv effects are retained as evidence but excluded from percentage scaling when level/base-stat context is unavailable.","Optimized profile selects compatible Soul → Martial Spirit → Mount slot-by-slot using the same mode score, records every selected item, then reranks the resulting mechanic vectors across the population.","Mount compatibility is treated as universal only because current Kaisen mount detail exposes no per-character restriction; this assumption is recorded on every mount."]}
                skill_rows=e.get("skills",[]) or []
                parsed_skill_count=sum(1 for s in skill_rows if any(v.get("effects") for v in s.get("versions",[]) or []))
                skill_coverage=parsed_skill_count/max(1,len(skill_rows))
                confidence=min(1.0,0.25+0.65*skill_coverage+0.10*min(parsed_skill_count,8)/8)
                e["analysis"].append({"ranking_key":"codex_analytical","title":f"Experimental Codex analysis — {mode} — {profile}","analysis_status":"experimental","mode_key":mode,"profile_key":profile,"tier_label":tier(p),"rank_order":pos,"total_score":round(score,3),"percentile":round(p,6),"confidence":round(confidence,3),"factors_json":json.dumps(factors,ensure_ascii=False),"evidence_json":json.dumps(evidence,ensure_ascii=False),"selected_subsystems":loadout["subsystems"] if loadout else [],"source_tiers_used":False})
                rows.append({"entity_id":e["id"],"name":e["canonical_name"],"tier":tier(p),"rank_order":pos,"score":round(score,3),"profile_key":profile,"selected_subsystems":loadout["subsystems"] if loadout else []})
            result_lists.append({"ranking_key":"codex_analytical","mode_key":mode,"profile_key":profile,"source_tiers_used":False,"entries":rows})
    for e in entities:
        if not any(a.get("ranking_key")=="codex_analytical" for a in e.get("analysis",[])):
            e.setdefault("analysis",[]).append({"ranking_key":"codex_analytical","title":"Codex analytical tier — generic — base","mode_key":"generic","profile_key":"base","tier_label":"UNRANKED","rank_order":None,"total_score":0,"confidence":0,"factors_json":"{}","evidence_json":json.dumps({"reason":"No sourced normalized kit effects"}),"source_tiers_used":False})
    return result_lists


def enrich_hero(e,detail,assets):
    api=f"{BASE}/api/album/{detail['id']}";retr=now();old_skills=e.get("skills") or []
    e["source_kits"]={"game8":old_skills,"kaisen_api_raw_skill_count":len((detail.get("meta") or {}).get("skills") or [])}
    ks=api_skills(detail)
    if ks:e["skills"]=ks
    meta=detail.get("meta") or {}
    e["kaisen_meta"]={k:meta.get(k) for k in ("templateId","name","kana","rarity","faction","stat","professions","cv","year","releaseDate","launchTime","kizunaFirstSeen","firstBannerStart","jpAssetId","shardsNeeded")}
    e["compatible_martial_spirits"]=[{"spirit_key":x.get("charName"),"name":clean(x.get("name")),"element":x.get("element"),"thumbnail":x.get("thumbnail")} for x in detail.get("compatibleWeapons") or []]
    bonds=[]
    for b in detail.get("bonds") or []:
        bonds.append({"relationship_type":"bond","bond_id":b.get("id"),"name":clean(b.get("name")),"members":b.get("members") or [],"buffs":b.get("buffs") or [],"source_site":"Kaisen Wiki","source_url":api})
    e["relationships"]=(e.get("relationships") or [])+bonds
    e.setdefault("provenance",[]).append(source("Kaisen Wiki",api,"character.detail",retr))
    # Prefer a Kaisen-native full illustration over a Game8/in-game capture when
    # the detail API exposes one. Existing source art remains as an alternate.
    has_kaisen_full=any(x.get("asset_type")=="full_art" and x.get("source_site")=="Kaisen Wiki" for x in e.get("images",[]))
    if not has_kaisen_full:
        for j,path in enumerate(detail.get("images") or []):
            try:m=save_asset(asset_url(path),assets,f"{hero_key(e)}-kaisen-full-{j}",1600)
            except Exception:m=None
            if m and m.get("height",1)>=m.get("width",1):
                for old in e.get("images",[]):
                    if old.get("display_role")=="detail_primary":
                        old["display_role"]="alternate_full_art"
                        old["priority"]=min(int(old.get("priority") or 100),100)
                e.setdefault("images",[]).append({"id":e["id"]*100+50+j,"image_key":f"kaisen-{hero_key(e)}-full-{j}","asset_type":"full_art","display_role":"detail_primary","priority":160,"source_site":"Kaisen Wiki",**m})
                break
    return len(ks)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--workers",type=int,default=8);args=ap.parse_args()
    out=Path(args.out);data_dir=out/"data";raw_dir=out/"raw"/"kaisen-api";assets=out/"assets";raw_dir.mkdir(parents=True,exist_ok=True);assets.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((data_dir/"catalog.json").read_text(encoding="utf-8"));entities=catalog.get("entities") or []
    pages={}
    for kind,path in LISTS.items():
        raw,_=kfetch_bytes(path);pages[kind]=raw.decode("utf-8","replace");save_raw(raw_dir,f"list-{kind}.html",raw)
    def hero_job(e):
        key=hero_key(e);path=f"/api/album/heroes-{key}"
        try:d,raw=kjson(path);return e,d,raw,None
        except Exception as exc:return e,None,None,str(exc)
    hero_fail=[];attr_map={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for idx,(e,d,raw,err) in enumerate(ex.map(hero_job,entities),1):
            if err or not d:
                hero_fail.append({"entity_id":e.get("id"),"name":e.get("canonical_name"),"key":hero_key(e),"error":err});continue
            save_raw(raw_dir,f"heroes-{hero_key(e)}.json",raw)
            for b in d.get("bonds") or []:
                for x in b.get("buffs") or []:
                    if x.get("attrId") is not None and x.get("attr"):attr_map[int(x["attrId"])]=clean(x["attr"])
            enrich_hero(e,d,assets)
            if idx%75==0:print(f"KAISEN_HERO_DETAIL {idx}/{len(entities)}",flush=True)
    soul_entries,soul_variants=parse_soul_list(pages["souls"]);spirit_entries=parse_spirit_list(pages["martial_spirit"]);mount_entries=parse_mount_list(pages["mount"])
    jobs=[]
    for x in soul_entries:jobs.append(("soul",x,f"/api/album/souls-{x['key']}"))
    for x in spirit_entries:jobs.append(("martial_spirit",x,f"/api/album/martial_spirit-{x['key']}"))
    for x in mount_entries:jobs.append(("mount",x,f"/api/album/transcendent-{x['key']}"))
    def subsystem_job(job):
        kind,entry,path=job;paths=[path]
        if kind=="martial_spirit" and not entry["key"].endswith("01"):paths.append(f"/api/album/martial_spirit-{entry['key']}01")
        last=None
        for p in paths:
            try:d,raw=kjson(p);return kind,entry,d,raw,p,None
            except Exception as exc:last=str(exc)
        return kind,entry,None,None,paths[0],last
    subs=[];sub_fail=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for idx,(kind,entry,d,raw,path,err) in enumerate(ex.map(subsystem_job,jobs),1):
            if not d:
                sub_fail.append({"type":kind,"key":entry["key"],"name":entry.get("name"),"error":err});continue
            save_raw(raw_dir,f"{kind}-{entry['key']}.json",raw)
            try:im=save_asset(entry.get("source_image"),assets,f"{kind}-{entry['key']}-card",700)
            except Exception:im=None
            subs.append(subsystem_record(kind,entry,d,soul_variants.get(entry["key"]) if kind=="soul" else None,im,attr_map))
            if idx%25==0:print(f"KAISEN_SUBSYSTEM_DETAIL {idx}/{len(jobs)}",flush=True)
    spirit_by_key={s["subsystem_key"]:s for s in subs if s["subsystem_type"]=="martial_spirit"}
    for e in entities:
        for x in e.get("compatible_martial_spirits") or []:
            k=x.get("spirit_key")
            if k in spirit_by_key:x["subsystem_key"]=k
            elif k and k.endswith("01") and k[:-2] in spirit_by_key:x["subsystem_key"]=k[:-2]
    tier_lists=compute_rankings(entities,subs)
    catalog["subsystems"]=subs;catalog["tier_lists"]=tier_lists;catalog["engine_version"]="0.7.0"
    catalog["analysis_policy"]={"source_tier_inputs":False,"ranking_basis":"Kaisen-normalized character kits plus transparent compatible subsystem mechanics","profiles":["base","optimized_subsystems"],"modes":list(MODE_WEIGHTS),"optimized_loadout_slots":["soul","martial_spirit","mount"],"mount_compatibility_assumption":"universal only because current Kaisen source exposes no per-character restriction"}
    catalog.setdefault("source_manifest",[]).extend([source("Kaisen Wiki",BASE+LISTS[k],f"subsystem.list.{k}") for k in ("souls","martial_spirit","mount")])
    full_count=sum(any(x.get("asset_type")=="full_art" for x in e.get("images",[])) for e in entities)
    ranked=sum(any(a.get("ranking_key")=="codex_analytical" and a.get("profile_key")=="optimized_subsystems" and a.get("tier_label")!="UNRANKED" for a in e.get("analysis",[])) for e in entities)
    report={"generated_at":now(),"canonical_heroes":len(entities),"hero_detail_api_success":len(entities)-len(hero_fail),"hero_detail_api_failures":hero_fail,"heroes_with_kaisen_skills":sum(bool(e.get("skills")) for e in entities),"heroes_ranked_with_subsystems":ranked,"heroes_with_full_art":full_count,"souls_logical_sets":sum(s["subsystem_type"]=="soul" for s in subs),"soul_visual_variants":sum(len(s.get("variants") or []) for s in subs if s["subsystem_type"]=="soul"),"martial_spirits":sum(s["subsystem_type"]=="martial_spirit" for s in subs),"mounts":sum(s["subsystem_type"]=="mount" for s in subs),"subsystem_api_failures":sub_fail,"source_tiers_used_for_analysis":False}
    catalog["games"][0]["data_report"]={**(catalog["games"][0].get("data_report") or {}),**report}
    (data_dir/"catalog.json").write_text(json.dumps(catalog,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (data_dir/"catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(catalog,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    (out/"kaisen-system-enrichment-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if len(hero_fail)>10:raise SystemExit("Too many Kaisen hero detail API failures")
    if report["souls_logical_sets"]<20 or report["martial_spirits"]<50 or report["mounts"]<10:raise SystemExit("Subsystem source capture incomplete")

if __name__=="__main__":main()
