#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, json
from pathlib import Path
from enrich_kaisen_systems import kjson, save_asset, asset_url, hero_key

def load_detail(root, key):
    local=root/"raw"/"kaisen-api"/f"heroes-{key}.json"
    if local.is_file():
        try:return json.loads(local.read_text(encoding="utf-8")),"local_raw"
        except Exception:pass
    detail,_=kjson(f"/api/album/heroes-{key}")
    return detail,"live_api"

def worker(root, e, assets):
    key=hero_key(e)
    # If the earlier Kaisen enrichment already cached a native full illustration,
    # just promote it. No network request is necessary.
    native=[x for x in e.get("images",[]) if x.get("asset_type")=="full_art" and x.get("source_site")=="Kaisen Wiki" and x.get("pack_path")]
    if native:
        native.sort(key=lambda x:int(x.get("priority") or 0),reverse=True)
        return e["id"],{"reuse_id":native[0].get("id")},None,"cached_native"
    try:
        detail,origin=load_detail(root,key)
    except Exception as exc:
        return e["id"],None,str(exc),"detail_failed"
    for j,path in enumerate(detail.get("images") or []):
        try:m=save_asset(asset_url(path),assets,f"{key}-kaisen-ui-refresh-{j}",1400)
        except Exception:continue
        if m and m.get("height",1)>=m.get("width",1):
            return e["id"],{"id":e["id"]*1000+800+j,"image_key":f"kaisen-{key}-ui-refresh-{j}","asset_type":"full_art","display_role":"detail_primary","priority":200,"source_site":"Kaisen Wiki",**m},None,origin
    return e["id"],None,"no vertical Kaisen detail image",origin

def promote(e,img):
    reuse_id=img.get("reuse_id") if img else None
    chosen=None
    if reuse_id is not None:
        chosen=next((x for x in e.get("images",[]) if x.get("id")==reuse_id),None)
    for old in e.get("images",[]) or []:
        if old.get("display_role")=="detail_primary":
            old["display_role"]="alternate_full_art"
            old["priority"]=min(int(old.get("priority") or 100),100)
    if chosen is not None:
        chosen["display_role"]="detail_primary";chosen["priority"]=200
    elif img:
        e.setdefault("images",[]).append(img)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--workers",type=int,default=24);args=ap.parse_args()
    root=Path(args.out);p=root/"data/catalog.json";assets=root/"assets"
    cat=json.loads(p.read_text(encoding="utf-8"));entities=cat.get("entities") or [];byid={e["id"]:e for e in entities}
    ok=0;reused=0;fail=[];origins={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures=[ex.submit(worker,root,e,assets) for e in entities]
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):
            eid,img,err,origin=f.result();e=byid[eid];origins[origin]=origins.get(origin,0)+1
            if img:
                if img.get("reuse_id") is not None:reused+=1
                promote(e,img);ok+=1
            elif err:fail.append({"entity_id":eid,"name":e.get("canonical_name"),"reason":err})
            if i%75==0:print("KAISEN_ART",i,len(entities),ok,"REUSED",reused,flush=True)
    p.write_text(json.dumps(cat,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (root/"data/catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(cat,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    report={"kaisen_detail_primary":ok,"reused_native_assets":reused,"origins":origins,"failed":fail}
    (root/"kaisen-art-refresh-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"detail_primary":ok,"reused":reused,"failed":len(fail),"origins":origins},ensure_ascii=False))
    if ok < 500:
        raise SystemExit(f"Too few Kaisen detail-primary visuals: {ok}/528")

if __name__=="__main__":main()
