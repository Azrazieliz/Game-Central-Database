#!/usr/bin/env python3
from pathlib import Path
import urllib.request, re
BASE="https://kaisen-wiki.h0rny.net"
UA="GameCodex/0.5 (+https://github.com/Azrazieliz/Game-Central-Database)"
targets={
 "hero-huamulan.html":BASE+"/heroes?entry=huamulan01",
 "souls.html":BASE+"/souls",
 "spirits.html":BASE+"/spirits",
 "mounts.html":BASE+"/transcendent",
 "hero-huamulan-detail.json":BASE+"/api/album/heroes-huamulan01",
 "soul-hubao-detail.json":BASE+"/api/album/souls-hubao",
 "spirit-blooddance-detail.json":BASE+"/api/album/martial_spirit-xuewutianhua01",
 "mount-dragons-detail.json":BASE+"/api/album/transcendent-babutianlong01",
 "album-page.txt":BASE+"/_next/static/chunks/app/"+"%28album%29/"+ "%5Bsection%5D/"+"page-b37d1f1971e5fd94.js",
}
out=Path("android/app/src/main/assets/codex/research");out.mkdir(parents=True,exist_ok=True)
for name,url in targets.items():
    try:
        req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8"})
        with urllib.request.urlopen(req,timeout=30) as r:
            body=r.read()
        (out/name).write_bytes(body)
        print("INSPECT_SAVED",name,len(body),url)
    except Exception as exc:
        print("INSPECT_FAILED",name,url,repr(exc))

# Fetch the exact album page bundle named by the current HTML.
hero_path=out/"hero-huamulan.html"
if hero_path.is_file():
    text=hero_path.read_text(encoding="utf-8")
    for src in re.findall(r'<script[^>]+src="([^"]+page-[^"]+\.js)"',text):
        if "/(album)/" not in src and "%28album%29" not in src:
            continue
        try:
            url=BASE+src if src.startswith("/") else src
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"*/*"})
            with urllib.request.urlopen(req,timeout=30) as r:
                body=r.read()
            (out/"album-page.js").write_bytes(body)
            print("INSPECT_SAVED","album-page.js",len(body),url)
            break
        except Exception as exc:
            print("INSPECT_FAILED","album-page.js",url,repr(exc))
