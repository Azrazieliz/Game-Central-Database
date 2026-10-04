#!/usr/bin/env python3
from __future__ import annotations

import argparse, concurrent.futures, hashlib, html, io, json, math, re, shutil, statistics, time, unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image
from pypinyin import lazy_pinyin
from pykakasi import kakasi

KAISEN_HEROES="https://kaisen-wiki.h0rny.net/heroes"
GAME8_HOME="https://game8.jp/shoujokaisen"
GAME8_CATALOG="https://game8.jp/shoujokaisen/419407"
UA="GameCodex/0.6 (+https://github.com/Azrazieliz/Game-Central-Database)"
FAC={"蜀":"shu","魏":"wei","吴":"wu","呉":"wu","群":"allied","漢":"han","使":"apostle","星":"star","時":"spacetime"}
ATTR_BY_COLOR={"#e0563b":"STR","#3fa8e0":"INT","#36c98e":"AGI"}
CAT_MARKERS={"通常攻撃":"normal","アクティブスキル":"active","パッシブスキル":"passive","パッシブ":"passive","桜花解放":"release"}
DESC_MARKERS=("％","%","ダメージ","敵","味方","付与","発動","回復","運命の輪","ターン","攻撃力","HP","落桜","無視","消去","解除","会心","状態異常","上昇","低下","戦闘不能")
MODE_WEIGHTS={
 "generic":{"damage":1.0,"survivability":1.0,"control":0.85,"utility":1.0,"counterplay":0.8,"reliability":1.0,"flexibility":0.9,"independence":0.8},
 "story":{"damage":1.0,"survivability":0.9,"control":0.8,"utility":1.0,"counterplay":0.6,"reliability":1.0,"flexibility":0.8,"independence":0.8},
 "pvp":{"damage":1.0,"survivability":1.05,"control":1.2,"utility":1.05,"counterplay":1.15,"reliability":1.0,"flexibility":1.0,"independence":0.8},
 "boss":{"damage":1.25,"survivability":1.0,"control":0.35,"utility":1.1,"counterplay":0.7,"reliability":1.0,"flexibility":0.75,"independence":0.8},
}
TIER_BANDS=((.97,"S+"),(.90,"S"),(.75,"A"),(.50,"B"),(.25,"C"),(0,"D"))

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def clean(s):
    return re.sub(r"\s+"," ",html.unescape(str(s or ""))).strip()

def norm_ascii(s):
    s=unicodedata.normalize("NFKC",str(s or "")).lower()
    return re.sub(r"[^a-z0-9]+","",s)

_kks=kakasi()
def romanize(s):
    s=clean(s)
    s=re.sub(r"（(?:UR[＋+](?:2026)?|UR|SSR|SR|R)）","",s)
    s=re.sub(r"\((?:UR\+?(?:2026)?|UR|SSR|SR|R)\)","",s,flags=re.I)
    pieces=[]
    for token in lazy_pinyin(s,errors=lambda x:[x]):
        for part in _kks.convert(token):
            pieces.append(part.get("hepburn") or part.get("orig") or "")
    return norm_ascii("".join(pieces))

def session():
    s=requests.Session()
    s.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8","Accept-Language":"ja,en-US;q=0.8,en;q=0.6"})
    return s

def fetch(sess,url,timeout=35):
    r=sess.get(url,timeout=timeout)
    r.raise_for_status()
    return r

def source_record(site,url,retrieved,kind):
    return {"site_name":site,"url":url,"retrieved_at":retrieved,"kind":kind,"conflict_status":"none"}

def load_kaisen_baseline(path, out_assets):
    root=Path(path)
    cat=json.loads((root/"data/catalog.json").read_text(encoding="utf-8"))
    entities=[]
    for src in cat.get("entities",[]):
        imgs=src.get("images") or []
        card=next((x for x in imgs if x.get("asset_type")=="card" or x.get("display_role")=="grid_card"),None)
        asset_url=(card or {}).get("source_url")
        stem=Path(urlparse(asset_url or src.get("entity_key","")).path).stem if asset_url else src.get("entity_key","").split(":")[-1]
        core=re.sub(r"^herocard_","",stem);core=re.sub(r"\d+$","",core)
        e={
          "id":int(src["id"]),"game_id":1,"entity_key":src.get("entity_key") or ("kaisen:"+stem),
          "canonical_name":src["canonical_name"],"display_name_status":"authoritative",
          "rarity_key":src.get("rarity_key"),"faction_key":src.get("faction_key"),"attribute_type":src.get("attribute_type"),
          "asset_url":asset_url,"asset_stem":stem,"match_key":norm_ascii(core),
          "aliases":[],"images":[],"skills":[],"signals":[],"relationships":[],"source_opinions":[],
          "provenance":list(src.get("provenance") or []),"analysis":[],"roster":[]
        }
        if card and card.get("pack_path"):
            source=root/card["pack_path"];target=out_assets/Path(card["pack_path"]).name
            if source.is_file():
                shutil.copy2(source,target)
                e["images"].append({**card,"pack_path":"assets/"+target.name})
        entities.append(e)
    if len(entities)<400:
        raise RuntimeError(f"Kaisen baseline incomplete: {len(entities)}")
    return entities

def parse_kaisen(sess):
    retrieved=now(); r=fetch(sess,KAISEN_HEROES); soup=BeautifulSoup(r.text,"html.parser")
    out=[]
    for i,b in enumerate(soup.select("button.silk-cardcell"),1):
        name=clean(b.get("title") or b.select_one(".kit-hpc-name").get_text(" ",strip=True) if b.select_one(".kit-hpc-name") else "")
        img=b.find("img",src=re.compile(r"/assets/thumbs/heroes_ui/cards/"))
        rarity=b.select_one(".kit-hpc-rar"); faction=b.select_one(".kit-faction-seal"); adot=b.select_one(".kit-hpc-adot")
        if not name or not img or not rarity: continue
        asset=urljoin(KAISEN_HEROES,img.get("src"))
        stem=Path(urlparse(asset).path).stem
        core=re.sub(r"^herocard_","",stem)
        core=re.sub(r"\d+$","",core)
        style=(adot.get("style") if adot else "") or ""
        cm=re.search(r"background\s*:\s*(#[0-9a-fA-F]{6})",style)
        out.append({
          "id":i,"game_id":1,"entity_key":"kaisen:"+stem,"canonical_name":name,"display_name_status":"authoritative",
          "rarity_key":clean(rarity.get_text()),"faction_key":FAC.get(clean(faction.get_text()) if faction else None),
          "attribute_type":ATTR_BY_COLOR.get(cm.group(1).lower()) if cm else None,
          "asset_url":asset,"asset_stem":stem,"match_key":norm_ascii(core),"aliases":[],"images":[],"skills":[],"signals":[],
          "relationships":[],"source_opinions":[],"provenance":[source_record("Kaisen Wiki",KAISEN_HEROES,retrieved,"character.catalog")],
          "analysis":[],"roster":[]
        })
    if len(out)<400: raise RuntimeError(f"Kaisen catalogue parse incomplete: {len(out)}")
    return out,r.text,retrieved

def parse_game8_catalog(sess):
    retrieved=now(); r=fetch(sess,GAME8_CATALOG); soup=BeautifulSoup(r.text,"html.parser")
    rows=[]; seen=set()
    for tr in soup.find_all("tr"):
        link=tr.find("a",href=re.compile(r"^/shoujokaisen/\d+$|^https://game8\.jp/shoujokaisen/\d+$"))
        if not link: continue
        imgs=tr.find_all("img")
        alts=[clean(x.get("alt")) for x in imgs]
        attr=next((x for x in ("敏捷","筋力","智力","知力") if x in alts),None)
        if not attr: continue
        url=urljoin(GAME8_CATALOG,link.get("href"))
        if url in seen: continue
        seen.add(url)
        name=clean(link.get_text(" ",strip=True))
        rowtext=clean(tr.get_text(" ",strip=True))
        roles=[x for x in ("アタッカー","サポーター","サポート","タンク","コントロール") if x in rowtext]
        faction=next((f for f in ("時","群","漢","蜀","魏","呉","吴","星") if re.search(rf"(?:^|\s){re.escape(f)}(?:\s|$)",rowtext)),None)
        rows.append({"url":url,"catalog_name":name,"attribute_source":attr,"roles_source":list(dict.fromkeys(roles)),"faction_source":faction})
    if len(rows)<150: raise RuntimeError(f"Game8 catalogue parse suspiciously small: {len(rows)}")
    return rows,r.text,retrieved

def lines_between(soup,start_pat,end_pat):
    all_lines=[clean(x) for x in soup.get_text("\n",strip=True).split("\n")]
    all_lines=[x for i,x in enumerate(all_lines) if x and (i==0 or x!=all_lines[i-1])]
    start=next((i for i,x in enumerate(all_lines) if re.search(start_pat,x)),None)
    if start is None:return []
    end=next((i for i,x in enumerate(all_lines[start+1:],start+1) if re.search(end_pat,x)),len(all_lines))
    return all_lines[start+1:end]

def looks_desc(s):
    return len(s)>=12 and any(m in s for m in DESC_MARKERS)

def parse_skills_dom(soup):
    skill_h2=next((h for h in soup.find_all("h2") if clean(h.get_text(" ",strip=True)).endswith("のスキル")),None)
    if not skill_h2:return []
    skills=[];cat=None;current=None;parts=[];ordinal=0

    def finish():
        nonlocal current,parts,ordinal
        if not current:return
        desc=clean(" ".join(parts))
        if looks_desc(desc):
            skills.append({"skill_key":f"{cat or 'unknown'}.{ordinal}","name":current,"skill_type":cat or "unknown","description_source":desc})
            ordinal+=1
        current=None;parts=[]

    for node in skill_h2.next_elements:
        if isinstance(node,Tag) and node is not skill_h2 and node.name=="h2":
            finish();break
        if isinstance(node,Tag) and node.name=="h3":
            finish()
            heading=clean(node.get_text(" ",strip=True))
            cat=CAT_MARKERS.get(heading,cat)
            continue
        if isinstance(node,Tag) and node.name=="img":
            alt=clean(node.get("alt"))
            if alt.endswith("のアイコン"):
                finish()
                current=alt[:-len("のアイコン")].strip()
                parts=[]
            continue
        if isinstance(node,NavigableString) and current:
            # Heading and image-alt text are handled structurally; only retain actual
            # prose after the skill marker.
            if node.find_parent(["h2","h3"]):continue
            t=clean(str(node))
            if not t or t in {"---",current} or t.endswith("のアイコン"):continue
            parts.append(t)
    finish()
    return skills

def infer_target(s):
    if "敵全体" in s:return {"side":"enemy","scope":"all"}
    m=re.search(r"敵(\d+)人",s)
    if m:return {"side":"enemy","count":int(m.group(1))}
    if "味方全体" in s or "味方全" in s:return {"side":"ally","scope":"all"}
    m=re.search(r"味方(\d+)人",s)
    if m:return {"side":"ally","count":int(m.group(1))}
    if "自身" in s or "自分" in s:return {"side":"self","count":1}
    return {}

def effect(sentence,etype,mkey,polarity=None,**extra):
    vals=[float(x) for x in re.findall(r"(\d+(?:\.\d+)?)%",sentence)]
    duration=re.search(r"(\d+)ターン",sentence)
    hits=re.search(r"(\d+)回(?:攻撃|ダメージ)",sentence)
    cond={}
    if "場合" in sentence: cond["conditional"]=True
    hp=re.search(r"HP(?:（%）|\(%\)|％|%)?が?(\d+(?:\.\d+)?)%以下",sentence)
    if hp:cond["target_hp_lte_percent"]=float(hp.group(1))
    return {"effect_type":etype,"mechanic_key":mkey,"polarity":polarity,"target":infer_target(sentence),
      "magnitude":{"percent_values":vals,**({"hits":int(hits.group(1))} if hits else {})},
      "condition":cond,"timing":({"duration_turns":int(duration.group(1))} if duration else {}),
      "extension":{"source_sentence":sentence},**extra}

def normalize_effects(text):
    out=[]
    sentences=[clean(x) for x in re.split(r"(?<=[。！？])|\n+",text) if clean(x)]
    for s in sentences:
        if "ダメージ" in s:
            out.append(effect(s,"damage","piercing_damage" if "貫通ダメージ" in s else "damage","negative"))
        if re.search(r"HP[^。]{0,28}回復|HPを\d+(?:\.\d+)?%回復|回復させる|回復する",s) and not any(x in s for x in ("回復不可","回復できない","回復量")):
            out.append(effect(s,"heal","healing","positive"))
        if "強化効果" in s and any(x in s for x in ("消去","解除","奪い取")):
            out.append(effect(s,"dispel","buff","negative"))
        if "状態異常" in s and any(x in s for x in ("消去","解除")):
            out.append(effect(s,"cleanse","status_effect","positive"))
        if "復活" in s or ("戦闘不能になった時" in s and "回復" in s):
            out.append(effect(s,"revive","revive","positive"))
        if "HPは1以下にならない" in s or "HPが1以下にならない" in s or "戦闘不能になるダメージ無効化" in s:
            out.append(effect(s,"immunity","death_prevention","positive"))
        if "ダメージ無効化" in s and "無視" not in s:
            out.append(effect(s,"immunity","damage_immunity","positive"))
        if "回復不可" in s or "禁療" in s:
            out.append(effect(s,"debuff","heal_block","negative"))
        if "被ダメージ" in s and re.search(r"被ダメージ[^。]{0,16}(?:-|減少|低下)",s):
            out.append(effect(s,"buff","damage_reduction","positive"))
        if "被ダメージ" in s and re.search(r"被ダメージ[^。]{0,16}(?:\+|増加|上昇)",s):
            out.append(effect(s,"debuff","damage_taken_up","negative"))
        if "攻撃力" in s and re.search(r"攻撃力[^。]{0,16}(?:\+|上昇|増加)",s):
            out.append(effect(s,"buff","attack_up","positive"))
        if "攻撃力" in s and re.search(r"攻撃力[^。]{0,16}(?:-|低下|減少)",s):
            out.append(effect(s,"debuff","attack_down","negative"))
        if "シールド" in s or ("盾" in s and "獲得" in s):
            out.append(effect(s,"shield","shield","positive"))
        if "落桜" in s:
            if any(x in s for x in ("付与","獲得")): out.append(effect(s,"resource_generate","sakura_petals","positive"))
            if any(x in s for x in ("失う","奪い取","消去","解除")): out.append(effect(s,"resource_consume","sakura_petals","negative"))
        if "桜花解放" in s and any(x in s for x in ("終わらせ","解除","中断")):
            out.append(effect(s,"counter","sakura_release","negative"))
        if "会心" in s and any(x in s for x in ("発動しない","発動不可")):
            out.append(effect(s,"debuff","crit_disable","negative"))
        if "追加" in s and "スキル" in s and "発動" in s:
            out.append(effect(s,"trigger","extra_skill_cast","positive"))
        if "無視" in s and any(x in s for x in ("ダメージ無効化","被会心ダメージ低下")):
            out.append(effect(s,"counter","defensive_immunity","positive"))
        statuses=list(dict.fromkeys(re.findall(r"「([^」]{1,40})」",s)))
        for status in statuses:
            mk="status:"+romanize(status) if romanize(status) else "status:"+hashlib.sha1(status.encode()).hexdigest()[:8]
            if re.search(rf"「{re.escape(status)}」(?:効果)?を付与",s):
                out.append(effect(s,"extension",mk,None,extension={"source_status_name":status,"signal_hint":"provides","source_sentence":s}))
            elif "場合" in s and re.search(rf"「{re.escape(status)}」",s):
                out.append(effect(s,"extension",mk,None,extension={"source_status_name":status,"signal_hint":"prefers","source_sentence":s}))
        if "状態異常" in s and any(x in s for x in ("数","付与されている場合","付与されている敵")):
            out.append(effect(s,"extension","status_effect",None,extension={"signal_hint":"prefers","source_sentence":s}))
    seen=set(); ded=[]
    for e in out:
        key=(e["effect_type"],e.get("mechanic_key"),json.dumps(e.get("target",{}),sort_keys=True),e["extension"].get("source_sentence",""))
        if key not in seen:seen.add(key);ded.append(e)
    return ded

def find_basic_table(soup):
    result={}
    for tr in soup.find_all("tr"):
        cells=[clean(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
        if len(cells)>=2 and cells[0] in {"キャラクター名","読み方","スキン名","CV","レア度","タイプ","勢力"}:
            result[cells[0]]=cells[1]
    return result

def choose_full_art(soup,source_name,rarity):
    # A Game8 page contains several images of the same character: eyecatch, icon/card and
    # the actual character illustration in the "基本情報" section. Only the latter is eligible
    # for detail_primary; a borderless/cropped card is not a substitute for full art.
    bad=("アイコン","図鑑","アイキャッチ","スキル","宝物","タップ","一覧","ランキング","バナー","広告")
    basic_imgs=set()
    basic_head=next((h for h in soup.find_all("h2") if clean(h.get_text(" ",strip=True)).endswith("の基本情報")),None)
    if basic_head:
        node=basic_head.next_sibling
        while node and not (getattr(node,"name",None)=="h2"):
            if getattr(node,"name",None)=="img":
                basic_imgs.add(id(node))
            if hasattr(node,"find_all"):
                for im in node.find_all("img"): basic_imgs.add(id(im))
            node=node.next_sibling
    candidates=[]
    for order,img in enumerate(soup.find_all("img")):
        alt=clean(img.get("alt"))
        src=img.get("data-src") or img.get("data-original") or img.get("src")
        if not src or not re.search(r"^https?://|^//|^/",src):continue
        if any(x in alt for x in bad):continue
        score=0
        if id(img) in basic_imgs:score+=300
        if source_name and source_name in alt:score+=100
        if rarity and rarity in alt:score+=15
        if alt.endswith("画像") and id(img) not in basic_imgs:score-=60
        if "少女廻戦" in alt:score+=10
        if "img.game8.jp" in src or "assets.game8.jp" in src:score+=15
        try:
            w=int(img.get("width") or 0);h=int(img.get("height") or 0)
            if h>w:score+=15
            score+=min((w*h)/100000,20)
        except:pass
        if score>30:candidates.append((score,-order,urljoin(GAME8_HOME,src),alt))
    return sorted(candidates,reverse=True)[0][2] if candidates else None

def parse_game8_page(sess,item):
    url=item["url"]; retrieved=now()
    try:r=fetch(sess,url)
    except Exception as e:return {**item,"error":str(e)}
    soup=BeautifulSoup(r.text,"html.parser")
    h1=clean((soup.find("h1") or {}).get_text(" ",strip=True) if soup.find("h1") else item["catalog_name"])
    rarity=(re.search(r"（(UR[＋+](?:2026)?|UR|SSR|SR|R)）",h1.replace("＋","+")) or [None,None])[1]
    basic=find_basic_table(soup)
    source_name=clean(basic.get("スキン名") or item["catalog_name"])
    source_name=re.sub(r"（(?:UR[＋+](?:2026)?|UR|SSR|SR|R)）","",source_name).strip()
    lines=lines_between(soup,r"のスキル$",r"の絆$")
    skills=parse_skills_dom(soup)
    for s in skills:s["versions"]=[{"effects":normalize_effects(s["description_source"])}]
    relationships=[]
    hs=soup.find_all(["h2","h3"])
    in_bonds=False
    for h in hs:
        txt=clean(h.get_text(" ",strip=True))
        if h.name=="h2":
            in_bonds=txt.endswith("の絆")
            continue
        if not in_bonds or h.name!="h3":continue
        parts=[];links=[];node=h.next_sibling
        while node and not (getattr(node,"name",None) in {"h2","h3"}):
            if hasattr(node,"get_text"):
                t=clean(node.get_text(" ",strip=True))
                if t:parts.append(t)
                for a in node.find_all("a",href=True) if hasattr(node,"find_all") else []:
                    if re.search(r"/shoujokaisen/\d+$",urlparse(urljoin(url,a["href"])).path):
                        links.append({"name":clean(a.get_text(" ",strip=True)),"url":urljoin(url,a["href"])})
            node=node.next_sibling
        relationships.append({"relationship_type":"bond","name":txt,"description_source":clean(" ".join(parts)),"members":links})
    return {**item,"html":r.text,"retrieved_at":retrieved,"h1":h1,"rarity_source":rarity,
      "character_name_source":clean(basic.get("キャラクター名")),"reading":clean(basic.get("読み方")),"skin_name_source":source_name,
      "cv":clean(basic.get("CV")),"skills":skills,"relationships":relationships,"full_art_url":choose_full_art(soup,source_name,rarity)}

def match_game8(entities,page,excluded_ids=None):
    excluded_ids=set(excluded_ids or ())
    keys=set()
    for v in (page.get("catalog_name"),page.get("skin_name_source"),page.get("character_name_source")):
        if v:
            keys.add(romanize(v));keys.add(norm_ascii(v))
    keys={k for k in keys if len(k)>=3}
    direct=[]
    for e in entities:
        if e["id"] in excluded_ids:
            continue
        nc=norm_ascii(e["canonical_name"])
        if nc in keys:
            direct.append((1.0,e))
    if len(direct)==1:
        return direct[0][1],1.0,"direct"
    scores=[]
    for e in entities:
        if e["id"] in excluded_ids:
            continue
        ek=e["match_key"]
        best=0.0
        for k in keys:
            ratio=SequenceMatcher(None,k,ek).ratio()
            if min(len(k),len(ek))>=6 and (k in ek or ek in k):
                ratio=max(ratio,min(len(k),len(ek))/max(len(k),len(ek)))
            best=max(best,ratio)
        if page.get("rarity_source") and e.get("rarity_key") and page["rarity_source"].replace("＋","+")!=e["rarity_key"].replace("＋","+"):
            best-=0.08
        scores.append((best,e))
    scores.sort(key=lambda x:x[0],reverse=True)
    if not scores:
        return None,0,"none"
    best,e=scores[0]
    second=scores[1][0] if len(scores)>1 else 0
    if best>=0.82 and best-second>=0.035:
        return e,best,"romanized"
    return None,best,"ambiguous"

def save_image(sess,url,outdir,key,max_dim=None,referer=None):
    if not url:return None
    headers={"Referer":referer} if referer else {}
    r=sess.get(url,timeout=45,headers=headers);r.raise_for_status()
    raw=r.content
    try:
        im=Image.open(io.BytesIO(raw));im.load()
        w,h=im.size
        if w<120 or h<120:return None
        if max_dim and max(w,h)>max_dim:
            scale=max_dim/max(w,h);im=im.resize((max(1,int(w*scale)),max(1,int(h*scale))),Image.Resampling.LANCZOS)
        if im.mode not in ("RGB","RGBA"):im=im.convert("RGBA" if "A" in im.mode else "RGB")
        name=hashlib.sha256((key+url).encode()).hexdigest()[:24]+".webp"
        path=outdir/name
        im.save(path,"WEBP",quality=84,method=6)
        data=path.read_bytes()
        return {"pack_path":"assets/"+name,"sha256":hashlib.sha256(data).hexdigest(),"byte_size":len(data),"width":im.width,"height":im.height}
    except Exception:
        ext=Path(urlparse(url).path).suffix.lower()
        if ext not in {".webp",".png",".jpg",".jpeg",".avif"}:ext=".img"
        name=hashlib.sha256((key+url).encode()).hexdigest()[:24]+ext
        path=outdir/name;path.write_bytes(raw)
        return {"pack_path":"assets/"+name,"sha256":hashlib.sha256(raw).hexdigest(),"byte_size":len(raw)}

def flatten_effects(e):
    return [(s,ef) for s in e.get("skills",[]) for v in s.get("versions",[]) for ef in v.get("effects",[])]

def breadth(ef):
    t=ef.get("target") or {}
    if t.get("scope")=="all":return 6.0
    return float(min(int(t.get("count") or 1),6))

def pct(ef):
    return [float(v) for v in (ef.get("magnitude") or {}).get("percent_values",[]) if isinstance(v,(int,float))]

def raw_features(e):
    effects=flatten_effects(e)
    vals={k:0.0 for k in MODE_WEIGHTS["generic"]}
    families=set(); conditions=0; independent=0
    evid={k:[] for k in vals}
    for s,ef in effects:
        et=ef.get("effect_type");mk=ef.get("mechanic_key");pv=pct(ef);b=breadth(ef)
        if et=="damage":
            coef=max(pv) if pv else 100;hits=float((ef.get("magnitude") or {}).get("hits") or 1);mul=1.15 if mk=="piercing_damage" else 1
            c=coef*hits*b*mul;vals["damage"]+=c;evid["damage"].append({"skill":s["name"],"mechanic":mk,"contribution":round(c,2)})
        rules={
         "survivability":{("heal","healing"):1,("shield","shield"):1,("buff","damage_reduction"):1.25,("revive","revive"):2,("immunity","death_prevention"):2,("immunity","damage_immunity"):1.75,("cleanse","status_effect"):.5},
         "control":{("debuff","heal_block"):1.25,("debuff","crit_disable"):1,("debuff","attack_down"):.75,("debuff","damage_taken_up"):.5},
         "utility":{("dispel","buff"):1,("cleanse","status_effect"):1,("resource_generate","sakura_petals"):.5,("resource_consume","sakura_petals"):.75,("buff","attack_up"):.75,("debuff","damage_taken_up"):.75,("trigger","extra_skill_cast"):.75},
         "counterplay":{("counter","sakura_release"):1.25,("counter","defensive_immunity"):1.25,("dispel","buff"):1,("cleanse","status_effect"):.75,("debuff","heal_block"):.75,("debuff","crit_disable"):.75,("immunity","damage_immunity"):.5,("immunity","death_prevention"):.5},
        }
        for feature,rr in rules.items():
            base=rr.get((et,mk))
            if base is not None:
                bonus=min(max(pv or [0])/100,2)*.25 if pv else 0;c=base+bonus;vals[feature]+=c;evid[feature].append({"skill":s["name"],"mechanic":mk,"contribution":round(c,3)})
        fmap={"damage":"damage","heal":"sustain","shield":"sustain","revive":"sustain","immunity":"sustain","buff":"support","cleanse":"support","dispel":"counterplay","counter":"counterplay","debuff":"control","resource_generate":"resource","resource_consume":"resource","trigger":"tempo"}
        if et in fmap:families.add(fmap[et])
        cond=1 if (ef.get("condition") or {}) else 0
        hint=(ef.get("extension") or {}).get("signal_hint")
        if hint in {"requires","prefers"}:cond+=1
        conditions+=cond
        independent+=0 if cond else 1
    vals["flexibility"]=float(len(families))
    if effects:
        vals["independence"]=independent/len(effects)
        byskill=defaultdict(list)
        for s,ef in effects:byskill[s["name"]].append(ef)
        for name,efs in byskill.items():
            bb=max(breadth(x) for x in efs); cc=min(1 if (x.get("condition") or {}) else 0 for x in efs)
            vals["reliability"]+=min(bb,6)/6/(1+cc)
    return vals,evid

def percentile_scores(raw_by_id):
    ids=list(raw_by_id); values=[raw_by_id[i] for i in ids]
    if not values:return {}
    if min(values)==max(values):
        c=0 if max(values)==0 else .5;return {i:c for i in ids}
    n=len(values);out={}
    for i,v in raw_by_id.items():
        less=sum(x<v for x in values);equal=sum(x==v for x in values);out[i]=(less+(equal-1)/2)/(n-1) if n>1 else 1
    return out

def tier(p):
    return next(label for threshold,label in TIER_BANDS if p>=threshold)

def compute_analysis(entities):
    eligible=[e for e in entities if len(e.get("skills",[]))>=2 and len(flatten_effects(e))>=3]
    raws={e["id"]:raw_features(e) for e in eligible}
    normalized={}
    for feature in MODE_WEIGHTS["generic"]:
        normalized[feature]=percentile_scores({eid:vals[0][feature] for eid,vals in raws.items()})
    for mode,weights in MODE_WEIGHTS.items():
        scored=[]
        for e in eligible:
            eid=e["id"];factors={};total=ws=0
            for feature,w in weights.items():
                raw=raws[eid][0][feature];ps=normalized[feature][eid];c=ps*w;total+=c;ws+=w
                factors[feature]={"raw":round(raw,4),"population_score":round(ps,6),"weight":w,"weighted_contribution":round(c,6)}
            scored.append((100*total/ws if ws else 0,e,factors,raws[eid][1]))
        scored.sort(key=lambda x:(-x[0],x[1]["id"]))
        n=len(scored)
        for pos,(score,e,factors,evidence) in enumerate(scored,1):
            p=1-(pos-1)/(n-1) if n>1 else 1
            completeness=min(len(e["skills"]),5)/5*.5+min(len(flatten_effects(e)),10)/10*.5
            e["analysis"].append({"title":f"Codex analytical tier — {mode}","mode_key":mode,"tier_label":tier(p),"rank_order":pos,"total_score":round(score,3),"percentile":round(p,6),"confidence":round(completeness,3),"factors_json":json.dumps(factors,ensure_ascii=False),"evidence_json":json.dumps(evidence,ensure_ascii=False),"source_tiers_used":False})
    for e in entities:
        if not e["analysis"]:
            e["analysis"].append({"title":"Codex analytical tier — generic","mode_key":"generic","tier_label":"UNRANKED","rank_order":None,"total_score":0,"confidence":0,"factors_json":"{}","evidence_json":json.dumps([{"reason":"insufficient normalized kit data"}]),"source_tiers_used":False})

def make_signals(e):
    sig={}
    def add(t,m,strength=1):
        k=(t,m);sig[k]=max(sig.get(k,0),strength)
    for s,ef in flatten_effects(e):
        et=ef.get("effect_type");mk=ef.get("mechanic_key");side=(ef.get("target") or {}).get("side");hint=(ef.get("extension") or {}).get("signal_hint")
        if hint in {"provides","requires","prefers","counters"}:add(hint,mk);continue
        if et in {"debuff"} and side in {"enemy",None}:add("provides",mk);add("provides","status_effect",.5)
        elif et in {"buff","shield","cleanse","heal","revive"} and side=="ally":add("provides",mk)
        elif et in {"dispel","counter"} and side in {"enemy",None}:add("counters",mk)
        elif et=="damage":add("provides",mk,.25)
    e["signals"]=[{"signal_type":t,"mechanic_key":m,"strength":v} for (t,m),v in sig.items()]

def compatibility(entities):
    for e in entities:make_signals(e)
    edges=[];idx={e["id"]:e for e in entities}
    ids=[e["id"] for e in entities if e["signals"]]
    for ix,a in enumerate(ids):
        sa=idx[a]["signals"]
        for b in ids[ix+1:]:
            sb=idx[b]["signals"];score=0;ev=[]
            for x in sa:
                for y in sb:
                    if x["mechanic_key"]!=y["mechanic_key"]:continue
                    for first,second,rev in ((x,y,False),(y,x,True)):
                        rule={("provides","requires"):(1,"enables requirement"),("provides","prefers"):(.6,"supports preferred mechanic")}.get((first["signal_type"],second["signal_type"]))
                        if rule:
                            c=rule[0]*min(first["strength"],second["strength"]);score+=c;ev.append({"mechanic_key":first["mechanic_key"],"contribution":round(c,3),"explanation":("reverse: " if rev else "")+rule[1]})
            if ev:edges.append({"from_entity_id":a,"to_entity_id":b,"mode_key":"generic","direction":"synergy","score":round(score,3),"evidence":ev})
    return edges

def infer_role(e):
    a=next((x for x in e["analysis"] if x["mode_key"]=="generic"),None)
    if not a or a["tier_label"]=="UNRANKED":return None
    f=json.loads(a["factors_json"]); ranked=sorted(((v["population_score"],k) for k,v in f.items() if k in {"damage","survivability","control","utility"}),reverse=True)
    if len(ranked)>1 and ranked[0][0]-ranked[1][0]<.12:return "hybrid"
    return {"damage":"damage","survivability":"tank","control":"control","utility":"support"}.get(ranked[0][1])

def save_game_icon(sess,outdir):
    try:
        soup=BeautifulSoup(fetch(sess,GAME8_HOME).text,"html.parser")
        img=next((x for x in soup.find_all("img") if "少女廻戦のロゴ" in clean(x.get("alt"))),None)
        if img:
            src=img.get("data-src") or img.get("src")
            if src:
                meta=save_image(sess,urljoin(GAME8_HOME,src),outdir,"game-icon",900,GAME8_HOME)
                if meta:return meta["pack_path"]
    except Exception:pass
    return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--workers",type=int,default=8);ap.add_argument("--kaisen-baseline");args=ap.parse_args()
    out=Path(args.out);assets=out/"assets";data=out/"data";raw=out/"raw";assets.mkdir(parents=True,exist_ok=True);data.mkdir(parents=True,exist_ok=True);raw.mkdir(parents=True,exist_ok=True)
    sess=session()
    if args.kaisen_baseline:
        entities=load_kaisen_baseline(args.kaisen_baseline,assets);khtml="";kret=now()
    else:
        entities,khtml,kret=parse_kaisen(sess);(raw/"kaisen-heroes.html").write_text(khtml,encoding="utf-8")
    catalog,ghtml,gret=parse_game8_catalog(sess);(raw/"game8-catalog.html").write_text(ghtml,encoding="utf-8")
    def worker(item):
        s=session();return parse_game8_page(s,item)
    pages=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i,p in enumerate(ex.map(worker,catalog),1):
            pages.append(p)
            if i%40==0:print(f"FETCH {i}/{len(catalog)}",flush=True)
    byid={e["id"]:e for e in entities};matches=[];unmatched=[];mapped_ids=set()
    for p in pages:
        if p.get("error"):unmatched.append({"url":p["url"],"name":p["catalog_name"],"reason":p["error"]});continue
        eid,confidence,method=match_game8(entities,p,mapped_ids)
        if not eid or eid["id"] in mapped_ids:
            unmatched.append({"url":p["url"],"name":p["catalog_name"],"best_score":round(confidence,3),"reason":"unmatched_or_duplicate"});continue
        mapped_ids.add(eid["id"]);e=eid
        alias=clean(p.get("skin_name_source") or p["catalog_name"])
        if alias and alias!=e["canonical_name"]:e["aliases"].append(alias)
        if p.get("character_name_source") and p["character_name_source"] not in e["aliases"] and p["character_name_source"]!=e["canonical_name"]:e["aliases"].append(p["character_name_source"])
        if p.get("reading"):e["aliases"].append(p["reading"])
        e["attribute_type"]=e.get("attribute_type") or {"筋力":"STR","智力":"INT","知力":"INT","敏捷":"AGI"}.get(p.get("attribute_source"))
        e["skills"]=p["skills"];e["relationships"]=p["relationships"]
        e["source_opinions"].append({"site_name":"Game8","kind":"catalog_roles","value":p.get("roles_source") or [],"source_url":p["url"],"reference_only":True})
        e["provenance"].append(source_record("Game8",p["url"],p["retrieved_at"],"character.kit"))
        e["source_urls"]={"kaisen":KAISEN_HEROES,"game8":p["url"]}
        if p.get("full_art_url"):e["_full_art_url"]=p["full_art_url"]
        matches.append({"entity_id":e["id"],"canonical_name":e["canonical_name"],"game8_name":p["catalog_name"],"url":p["url"],"confidence":round(confidence,3),"method":method,"skills":len(e["skills"])})
        (raw/f"game8-{urlparse(p['url']).path.rsplit('/',1)[-1]}.html").write_text(p["html"],encoding="utf-8")
    print(json.dumps({"kaisen_entities":len(entities),"game8_discovered":len(catalog),"game8_fetched":len(pages),"mapped":len(matches),"unmatched":len(unmatched),"with_skills":sum(bool(e["skills"]) for e in entities)},ensure_ascii=False),flush=True)
    # visuals: the validated baseline already carries card tiles. Download Game8
    # detail art concurrently so the build does not serialize hundreds of image requests.
    for e in entities:
        if not any(x.get("display_role")=="grid_card" for x in e["images"]) and e.get("asset_url"):
            try:
                m=save_image(sess,e["asset_url"],assets,e["entity_key"]+"-card",900,KAISEN_HEROES)
                if m:e["images"].append({"id":e["id"]*10+1,"image_key":e["entity_key"]+"-card","asset_type":"card","display_role":"grid_card","priority":100,"source_url":e["asset_url"],**m})
            except Exception:pass

    full_jobs=[(e,e.pop("_full_art_url",None)) for e in entities]
    full_jobs=[(e,u) for e,u in full_jobs if u]
    def full_worker(pair):
        e,u=pair
        try:
            s=session()
            m=save_image(s,u,assets,e["entity_key"]+"-full",1600,e.get("source_urls",{}).get("game8"))
            return e["id"],u,m
        except Exception:
            return e["id"],u,None
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(4,args.workers)) as ex:
        for i,(eid,u,m) in enumerate(ex.map(full_worker,full_jobs),1):
            if m and m.get("height",0)>m.get("width",0):
                e=byid[eid]
                e["images"].append({"id":e["id"]*10+2,"image_key":e["entity_key"]+"-full","asset_type":"full_art","display_role":"detail_primary","priority":100,"source_url":u,**m})
            if i%50==0:print(f"FULL_ART {i}/{len(full_jobs)}",flush=True)
    compute_analysis(entities)
    for e in entities:e["role_key"]=infer_role(e)
    edges=compatibility(entities)
    icon=save_game_icon(sess,assets)
    generated=now()
    tiers=[]
    for mode in MODE_WEIGHTS:
        rows=[{"entity_id":e["id"],"name":e["canonical_name"],"tier":a["tier_label"],"rank_order":a["rank_order"],"score":a["total_score"]} for e in entities for a in e["analysis"] if a["mode_key"]==mode and a["tier_label"]!="UNRANKED"]
        tiers.append({"ranking_key":"codex_analytical","mode_key":mode,"source_tiers_used":False,"entries":sorted(rows,key=lambda x:x["rank_order"] or 10**9)})
    report={"generated_at":generated,"kaisen_entities":len(entities),"game8_discovered":len(catalog),"game8_mapped":len(matches),"game8_unmatched":len(unmatched),"characters_with_normalized_skills":sum(bool(e["skills"]) for e in entities),"characters_ranked":sum(any(a["tier_label"]!="UNRANKED" for a in e["analysis"]) for e in entities),"characters_with_full_art":sum(any(i["asset_type"]=="full_art" for i in e["images"]) for e in entities),"source_tiers_used_for_analysis":False,"unmatched":unmatched[:200]}
    cat={"generated_at":generated,"engine_version":"0.6.0","games":[{"id":1,"game_key":"shoujo_kaisen","name":"Shoujo Kaisen","adapter_key":"shoujo_kaisen","icon_path":icon,"character_count":len(entities),"data_report":report}],"patches":[],"entities":entities,"unresolved_entity_count":len(unmatched),"unresolved_entities":unmatched,"compatibility":edges,"tier_lists":tiers,"roster_accounts":[],"source_manifest":[source_record("Kaisen Wiki",KAISEN_HEROES,kret,"character.catalog"),source_record("Game8",GAME8_CATALOG,gret,"character.catalog")],"analysis_policy":{"source_tier_inputs":False,"ranking_basis":"normalized kits only","modes":list(MODE_WEIGHTS)}}
    (data/"catalog.json").write_text(json.dumps(cat,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (data/"catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(cat,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    (out/"source-sync-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"identity-match-report.json").write_text(json.dumps({"matched":matches,"unmatched":unmatched},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if report["characters_with_normalized_skills"]<120:
        raise SystemExit("Too few normalized kits; refusing data-complete build")
    if report["characters_ranked"]<120:
        raise SystemExit("Too few analytical rankings; refusing data-complete build")

if __name__=="__main__":main()
