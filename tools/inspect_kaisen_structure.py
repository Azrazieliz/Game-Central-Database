#!/usr/bin/env python3
from pathlib import Path
import urllib.request
BASE="https://kaisen-wiki.h0rny.net"
UA="GameCodex/0.5 (+https://github.com/Azrazieliz/Game-Central-Database)"
targets={
 "hero-huamulan.html":BASE+"/heroes?entry=huamulan01",
 "souls.html":BASE+"/souls",
 "spirits.html":BASE+"/spirits",
 "mounts.html":BASE+"/transcendent",
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
