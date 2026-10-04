#!/usr/bin/env python3
from pathlib import Path
import requests
BASE="https://kaisen-wiki.h0rny.net"
UA="GameCodex/0.6 (+https://github.com/Azrazieliz/Game-Central-Database)"
targets={
 "hero-huamulan.html":BASE+"/heroes?entry=huamulan01",
 "souls.html":BASE+"/souls",
 "spirits.html":BASE+"/spirits",
 "mounts.html":BASE+"/transcendent",
}
out=Path("android/app/src/main/assets/codex/research");out.mkdir(parents=True,exist_ok=True)
s=requests.Session();s.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,*/*;q=0.8"})
for name,url in targets.items():
    try:
        r=s.get(url,timeout=30);r.raise_for_status()
        (out/name).write_text(r.text,encoding="utf-8")
        print("INSPECT_SAVED",name,len(r.text),url)
    except Exception as exc:
        print("INSPECT_FAILED",name,url,repr(exc))
