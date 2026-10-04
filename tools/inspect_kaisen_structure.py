#!/usr/bin/env python3
import re, requests
from bs4 import BeautifulSoup
BASE="https://kaisen-wiki.h0rny.net"
UA="GameCodex-inspect/1.0"
s=requests.Session();s.headers.update({"User-Agent":UA})
urls=[
 BASE+"/heroes?entry=huamulan01",
 BASE+"/souls",
 BASE+"/spirits",
 BASE+"/transcendent",
]
for url in urls:
    r=s.get(url,timeout=30);r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    print("\n===URL",url,"BYTES",len(r.text),"TITLE",soup.title.get_text(" ",strip=True) if soup.title else "","===")
    print("ENTRY_LINKS",[(a.get_text(" ",strip=True)[:60],a.get("href")) for a in soup.find_all("a",href=True) if "entry=" in a.get("href","")][:20])
    print("BUTTONS",[(b.get("class"),b.get("title"),b.get("data-entry"),b.get("data-key")) for b in soup.find_all("button")[:15]])
    print("DETAIL_CLASSES",sorted({cl for tag in soup.find_all(True) for cl in (tag.get("class") or []) if any(k in cl.lower() for k in ("detail","skill","effect","soul","spirit","mount","hero","stat"))})[:120])
    for needle in ("Hua Mulan","huamulan01","Skill","skill","Effect","effect","Attack","ATK","HP","Description","description"):
        p=r.text.find(needle)
        if p>=0:
            print("CONTEXT",needle,repr(re.sub(r"\s+"," ",r.text[max(0,p-900):p+2500]))[:3600])
            break
    # first five candidate card images and containing element snippets
    imgs=[im for im in soup.find_all("img") if any(x in (im.get("src") or "") for x in ("heroes_ui/cards","souls/","martial_spirit_ui/cards","transcendent_ui/cards"))]
    for im in imgs[:5]:
        par=im
        for _ in range(4):
            if getattr(par,"parent",None):par=par.parent
        print("CARD",im.get("alt"),im.get("src"),"PARENT",re.sub(r"\s+"," ",str(par))[:1800])
