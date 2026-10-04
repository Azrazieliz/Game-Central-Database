#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, mimetypes, re, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone

UA = 'GameCodex/0.5 (+https://github.com/Azrazieliz/Game-Central-Database)'
HEROES = 'https://kaisen-wiki.h0rny.net/heroes'
FAC = {'蜀':'shu','魏':'wei','吴':'wu','呉':'wu','群':'allied','漢':'han','使':'apostle','星':'star'}
RAR = r'(?:UR\+2026|UR\+|UR|SSR|SR|R)'

class P(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base=base; self.order=0; self.stack=[]; self.links=[]; self.texts=[]
    def handle_starttag(self, tag, attrs):
        self.order += 1; d=dict(attrs); self.stack.append((tag,self.order,d,[]))
        if tag=='img':
            src=d.get('src') or d.get('data-src') or d.get('data-lazy-src')
            if src: self.links.append({'order':self.order,'href':urllib.parse.urljoin(self.base,src),'text':d.get('alt',''),'kind':'img'})
    def handle_data(self, data):
        t=' '.join(data.split())
        if t:
            self.order += 1; self.texts.append({'order':self.order,'text':t})
            for i in range(len(self.stack)): self.stack[i][3].append(t)
    def handle_endtag(self, tag):
        self.order += 1
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                node=self.stack.pop(i); txt=' '.join(node[3]).strip()
                if tag=='a' and node[2].get('href'):
                    self.links.append({'order':node[1],'href':urllib.parse.urljoin(self.base,node[2]['href']),'text':txt,'kind':'a'})
                break

def get(url, timeout=30):
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get_content_type()

def parse_heroes(body):
    p=P(HEROES); p.feed(body.decode('utf-8','replace'))
    assets=sorted([x for x in p.links if x['kind']=='a' and '/assets/thumbs/heroes_ui/cards/' in urllib.parse.urlparse(x['href']).path and re.search(r'\.(?:webp|png|jpe?g|avif)$',x['href'],re.I)],key=lambda x:x['order'])
    if not assets:
        assets=sorted([x for x in p.links if x['kind']=='img' and '/assets/thumbs/heroes_ui/cards/' in urllib.parse.urlparse(x['href']).path],key=lambda x:x['order'])
    out=[]; seen=set()
    for i,a in enumerate(assets):
        end=assets[i+1]['order'] if i+1<len(assets) else 10**12
        texts=[x['text'] for x in p.texts if a['order'] < x['order'] < end]
        fri=next((j for j,t in enumerate(texts) if re.fullmatch(rf'[蜀魏吴呉群漢使星]{RAR}',re.sub(r'\s+','',t).replace('＋','+'))),None)
        if fri is None: continue
        candidates=[t for t in texts[:fri] if t.lower() not in {'image','heroes','newest','oldest'} and not re.fullmatch(rf'[蜀魏吴呉群漢使星]{RAR}',re.sub(r'\s+','',t).replace('＋','+'))]
        if not candidates: continue
        name=candidates[-1].strip()
        fr=re.sub(r'\s+','',texts[fri]).replace('＋','+')
        faction=FAC.get(fr[0]); rarity=fr[1:]
        asset=a['href']; key=Path(urllib.parse.urlparse(asset).path).stem
        sig=(key,name,rarity)
        if sig in seen: continue
        seen.add(sig); out.append({'entry_key':key,'name':name,'faction':faction,'rarity':rarity,'asset_url':asset})
    return out

def save_asset(url, outdir):
    data,ctype=get(url,45)
    ext=Path(urllib.parse.urlparse(url).path).suffix.lower()
    if ext not in {'.webp','.png','.jpg','.jpeg','.avif'}:
        ext=mimetypes.guess_extension(ctype or '') or '.img'
    name=hashlib.sha256(url.encode()).hexdigest()[:24]+ext
    path=outdir/name
    if not path.exists(): path.write_bytes(data)
    return 'assets/'+name, hashlib.sha256(data).hexdigest(), len(data)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--max',type=int,default=0); args=ap.parse_args()
    out=Path(args.out); assets=out/'assets'; data_dir=out/'data'; assets.mkdir(parents=True,exist_ok=True); data_dir.mkdir(parents=True,exist_ok=True)
    body,_=get(HEROES); heroes=parse_heroes(body)
    if not heroes:
        sample=body.decode('utf-8','replace')[:12000]
        print('KAISEN_HTML_BYTES', len(body))
        print('KAISEN_HTML_SAMPLE_BEGIN')
        print(sample)
        print('KAISEN_HTML_SAMPLE_END')
    if args.max: heroes=heroes[:args.max]
    entities=[]; failures=[]
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for idx,h in enumerate(heroes,1):
        images=[]
        try:
            pack_path,sha,size=save_asset(h['asset_url'],assets)
            images=[{'id':idx,'image_key':h['entry_key']+'-card','asset_type':'card','display_role':'grid_card','priority':100,'source_url':h['asset_url'],'pack_path':pack_path,'sha256':sha,'byte_size':size}]
        except Exception as e:
            failures.append({'name':h['name'],'url':h['asset_url'],'error':str(e)})
        entities.append({'id':idx,'game_id':1,'entity_key':'kaisen:'+h['entry_key'],'canonical_name':h['name'],'display_name_status':'authoritative','rarity_key':h['rarity'],'faction_key':h['faction'],'role_key':None,'attribute_type':None,'aliases':[],'images':images,'versions':[],'skills':[],'signals':[],'relationships':[],'source_opinions':[],'provenance':[{'site_name':'Kaisen Wiki','fact_key':'character.name','conflict_status':'none','url':HEROES,'retrieved_at':now}],'analysis':[],'roster':[]})
    catalog={'generated_at':now,'engine_version':'0.5.0-bootstrap','games':[{'id':1,'game_key':'shoujo_kaisen','name':'Shoujo Kaisen','adapter_key':'shoujo_kaisen'}],'patches':[],'entities':entities,'unresolved_entity_count':0,'unresolved_entities':[],'compatibility':[],'tier_lists':[],'roster_accounts':[],'bootstrap':{'source':HEROES,'character_count':len(entities),'asset_failures':failures,'note':'Kaisen Wiki canonical names/cards bootstrap. Kit analysis is populated by the full engine pipeline, never from source tier labels.'}}
    (data_dir/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    (data_dir/'catalog.js').write_text('window.CODEX_CATALOG='+json.dumps(catalog,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
    (out/'source-sync-report.json').write_text(json.dumps(catalog['bootstrap'],ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'characters':len(entities),'assets_ok':sum(bool(e['images']) for e in entities),'asset_failures':len(failures)},ensure_ascii=False))
    if len(entities)<400: raise SystemExit(f'Only {len(entities)} characters parsed; refusing to build a misleading full DB')

if __name__=='__main__':
    main()
