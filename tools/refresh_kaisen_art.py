#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, json
from pathlib import Path
from enrich_kaisen_systems import kjson, save_asset, asset_url, hero_key

def worker(e, assets):
    key=hero_key(e)
    try:
        detail,_=kjson(f"/api/album/heroes-{key}")
    except Exception as exc:
        return e["id"],None,str(exc)
    for j,path in enumerate(detail.get("images") or []):
        try:m=save_asset(asset_url(path),assets,f"{key}-kaisen-ui-refresh-{j}",1600)
        except Exception:continue
        if m and m.get("height",1)>=m.get("width",1):
            return e["id"],{"id":e["id"]*1000+800+j,"image_key":f"kaisen-{key}-ui-refresh-{j}","asset_type":"full_art","display_role":"detail_primary","priority":200,"source_site":"Kaisen Wiki",**m},None
    return e["id"],None,"no vertical Kaisen detail image"

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--workers",type=int,default=8);args=ap.parse_args()
    root=Path(args.out);p=root/"data/catalog.json";assets=root/"assets"
    cat=json.loads(p.read_text(encoding="utf-8"));entities=cat.get("entities") or [];byid={e["id"]:e for e in entities}
    ok=0;fail=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures=[ex.submit(worker,e,assets) for e in entities]
        for i,f in enumerate(concurrent.futures.as_completed(futures),1):
            eid,img,err=f.result();e=byid[eid]
            if img:
                for old in e.get("images") or []:
                    if old.get("display_role")=="detail_primary":
                        old["display_role"]="alternate_full_art";old["priority"]=min(int(old.get("priority") or 100),100)
                e.setdefault("images",[]).append(img);ok+=1
            elif err:fail.append({"entity_id":eid,"name":e.get("canonical_name"),"reason":err})
            if i%75==0:print("KAISEN_ART",i,len(entities),ok,flush=True)
    p.write_text(json.dumps(cat,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    (root/"data/catalog.js").write_text("window.CODEX_CATALOG="+json.dumps(cat,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    report={"kaisen_detail_primary_refreshed":ok,"failed":fail}
    (root/"kaisen-art-refresh-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"refreshed":ok,"failed":len(fail)},ensure_ascii=False))

if __name__=="__main__":main()
