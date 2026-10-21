#!/usr/bin/env python3
"""Build expandable searchable historical documents website; Python standard library only."""
import argparse, collections, datetime, hashlib, html, json, os, pathlib, re, shutil, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
CACHE = ROOT/'cache'
OUT = ROOT/'public'
HTML = lambda value: html.escape(str(value), quote=True)
CSS = '''*{box-sizing:border-box}body{margin:0;font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif;background:#f6f4ef;color:#252c35}a{color:#184b69}a:hover{text-decoration-thickness:2px}.shell{max-width:1050px;padding:0 20px;margin:auto}header{background:#152c3c;color:#f7f4ee;padding:19px 0}header a{color:#fff;text-decoration:none}header nav{display:flex;gap:22px;flex-wrap:wrap}header h1{font-size:1.25rem;margin:0 0 8px}.hero{padding:46px 0 26px}.eyebrow{text-transform:uppercase;letter-spacing:.1em;color:#756449;font-size:.8rem;font-weight:700}.hero h2{font:700 clamp(2rem,5vw,3.5rem)/1.1 Georgia,serif;margin:10px 0}.muted{color:#536373}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:15px;margin:20px 0 40px}.card{background:white;border:1px solid #ddd9cf;border-radius:10px;padding:20px}.card h3{margin:0 0 6px}.pill{border:1px solid #bac8c9;border-radius:20px;padding:3px 9px;font-size:.82rem;display:inline-block}.notice{border-left:4px solid #ad8a44;background:#fff5d9;padding:13px 18px}.panel{background:white;padding:22px;border:1px solid #e2ded6;border-radius:12px;margin:20px 0}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}input,select,button{font:inherit;padding:11px;border-radius:7px;border:1px solid #aeb6b8}input{min-width:200px;flex:1}button{background:#174660;color:white;cursor:pointer}.docs{display:grid;gap:12px}.document{padding:13px 0;border-bottom:1px solid #ddd}.document h3{margin:0}.textpage{white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.55 ui-monospace,Consolas,monospace;color:#29313a}.pager{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}footer{border-top:1px solid #c9c4ba;margin-top:60px;padding:30px 0;font-size:.85rem;color:#52606c}@media(max-width:500px){.hero{padding-top:25px}.shell{padding:0 14px}.panel{padding:13px}}'''

def page(title, body, base='/', description='', extra_head=''):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{HTML(title)} — {HTML(SOURCE['site_title'])}</title><meta name="description" content="{HTML(description or title)}"><link rel="stylesheet" href="/style.css">{extra_head}</head><body><header><div class="shell"><h1><a href="/">{HTML(SOURCE['site_title'])}</a></h1><nav><a href="/">Home</a><a href="/collections/">Collections</a><a href="/search/">Search transcripts</a><a href="https://archive.org/details/@joe_augstell" rel="noopener">Internet Archive profile ↗</a></nav></div></header><main class="shell">{body}</main><footer><div class="shell">Research and collection contribution: {HTML(SOURCE['byline'])}. Government source documents retain their original authorship. OCR may be inaccurate; consult original scans.</div></footer></body></html>'''

def write(path, text):
    dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text,encoding='utf-8')

def download_text(archive_id):
    CACHE.mkdir(exist_ok=True)
    cache=CACHE/(archive_id+'.txt')
    if cache.exists() and cache.stat().st_size>100: return cache.read_text(encoding='utf-8',errors='replace'), 'cached OCR'
    url='https://archive.org/metadata/'+urllib.parse.quote(archive_id)
    def retrieve(url):
        req=urllib.request.Request(url, headers={'User-Agent':'MagaddinoHistoricalArchive/1.0 (historical transcript mirror)'})
        err=None
        for delay in (0,2,5):
            if delay: time.sleep(delay)
            try:
                with urllib.request.urlopen(req,timeout=90) as response:return response.read()
            except (urllib.error.URLError, TimeoutError) as exc:err=exc
        raise RuntimeError(f'{url}: {err}')
    try:
        metadata=json.loads(retrieve(url))
        files=metadata.get('files',[])
        candidates=[f for f in files if f.get('name','').lower().endswith(('_djvu.txt','_text.txt'))]
        if not candidates:
            candidates=[f for f in files if f.get('name','').lower().endswith('.txt') and 'meta' not in f.get('name','').lower() and 'readme' not in f.get('name','').lower()]
        if not candidates: return None,'No OCR text derivative found'
        filename=sorted(candidates,key=lambda f: (0 if f['name'].lower().endswith('_djvu.txt') else 1,len(f['name'])))[0]['name']
        doc_url='https://archive.org/download/'+urllib.parse.quote(archive_id)+'/'+urllib.parse.quote(filename)
        raw=retrieve(doc_url)
        if len(raw)<100: return None,'OCR text too short; check item'
        cache.write_bytes(raw)
        return raw.decode('utf-8',errors='replace'),'downloaded OCR'
    except Exception as exc:return None,f'Download not available: {exc}'

def split_text(ocr, max_chars=9000):
    """Use form-feed page boundaries if present; otherwise use explicitly labeled chunks."""
    ff=re.split(r'\f',ocr)
    if len(ff)>2:
        out=[t.strip() for t in ff]
        # Preserve exact page order; empty OCR pages remain represented.
        return [(f'OCR page {i+1}',t or '[No OCR text detected]',i+1) for i,t in enumerate(out)]
    # text without page boundaries: divide on line boundaries and label *segments*, not fabricated page references.
    lines=ocr.splitlines(keepends=True);groups=[];buf=[];count=0
    for line in lines:
        if buf and count+len(line)>max_chars:
            groups.append(''.join(buf));buf=[];count=0
        if len(line)>max_chars:
            for j in range(0,len(line),max_chars):
                part=line[j:j+max_chars]
                if buf:groups.append(''.join(buf));buf=[];count=0
                groups.append(part)
        else:buf.append(line);count+=len(line)
    if buf:groups.append(''.join(buf))
    return [(f'OCR text segment {i+1}',t,None) for i,t in enumerate(groups)]

def search_tokens(txt):
    return set(re.findall(r'[a-z0-9]{3,}',txt.lower()))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--offline',action='store_true',help='Build homepage and collections without downloading OCR');ap.add_argument('--base-url',default='https://example.pages.dev',help='Public website URL for sitemap');args=ap.parse_args()
    if OUT.exists():shutil.rmtree(OUT)
    OUT.mkdir();write('style.css',CSS)
    docs=[];index=collections.defaultdict(list);status=[];all_urls=['/','/collections/','/search/']
    collcards=[];collection_links=[]
    for collection in SOURCE['collections']:
        cid=collection['id'];items_html=[]
        collection_links.append(f'<a href="/collections/{cid}/">{HTML(collection["title"])}</a>')
        for item in collection['items']:
            iid=item['id']; aid=item['archive_id'];base=f'collections/{cid}/{iid}/';sourceurl=f'https://archive.org/details/{urllib.parse.quote(aid)}'
            textval, state=(None,'Offline preview: OCR not downloaded') if args.offline else download_text(aid)
            chunks=split_text(textval) if textval else []
            status.append({'collection':cid,'item':iid,'archive_id':aid,'state':state,'ocr_segments':len(chunks),'contains_form_feed_pages':bool(chunks and chunks[0][2])})
            cards=[]
            for n,(label,block,number) in enumerate(chunks,1):
                rel=base+f'text-{n:04d}/';all_urls.append('/'+rel)
                docid=len(docs)
                docs.append({'url':'/'+rel,'title':f'{collection["title"]} — {item["title"]}, {label}','collection':cid,'text':block})
                for token in search_tokens(block):index[token].append(docid)
                scanlink=(sourceurl+f'/page/n{number-1}/mode/1up' if number else sourceurl)
                write(rel+'index.html',page(f'{item["title"]}: {label}',f'''<p><a href="/collections/{cid}/">{HTML(collection['title'])}</a> / <a href="/{base}">{HTML(item['title'])}</a></p><h2>{HTML(item['title'])} — {HTML(label)}</h2><p><a href="{HTML(scanlink)}">View original scan ↗</a> · <a href="{HTML(sourceurl)}">Internet Archive item ↗</a></p><div class="notice">Uncorrected machine-generated OCR. Some words, names and dates may be wrong. The original page scan is authoritative.</div><article class="panel textpage">{HTML(block)}</article><nav class="pager">{('<a href="/'+base+f'text-{n-1:04d}/">← Previous</a>') if n>1 else ''} {('<a href="/'+base+f'text-{n+1:04d}/">Next →</a>') if n<len(chunks) else ''}</nav>''', description=f'Original FBI text transcription: {item["title"]}, {label}, contributed by {SOURCE["byline"]}'))
                cards.append(f'<a href="/{rel}">{HTML(label)}</a>')
            info=f'{len(chunks)} searchable OCR {"pages" if chunks and chunks[0][2] else "text segments"}' if chunks else f'OCR not yet imported — {HTML(state)}'
            item_body=f'''<div class="hero"><p class="eyebrow">{HTML(collection['title'])}</p><h2>{HTML(item['title'])}</h2><p><span class="pill">{HTML(info)}</span> <span class="pill">{item.get('expected_pages','?')} source pages (previous audit)</span></p><p><a href="{HTML(sourceurl)}">View original on Internet Archive ↗</a></p></div><div class="notice">The original FBI generated these records; {HTML(SOURCE['byline'])} is credited for collection and online publication. OCR text has not been proofread.</div><div class="panel"><h3>Read transcriptions</h3>{('<div class="docs">'+''.join('<div>'+x+'</div>' for x in cards)+'</div>') if cards else '<p>No transcripts bundled in this preview. Run the builder with Internet access to fetch existing Archive.org OCR automatically.</p>'}</div>'''
            write(base+'index.html',page(item['title'],item_body))
            all_urls.append('/'+base)
            items_html.append(f'<div class="card"><h3><a href="/{base}">{HTML(item["title"])}</a></h3><p>{HTML(info)}</p><a href="{HTML(sourceurl)}">Original scan ↗</a></div>')
        write(f'collections/{cid}/index.html',page(collection['title'],f'<section class="hero"><p class="eyebrow">Collection</p><h2>{HTML(collection["title"])}</h2><p>{HTML(collection.get("description",""))}</p></section><div class="cards">{"".join(items_html)}</div>'))
        all_urls.append(f'/collections/{cid}/')
        collcards.append(f'<div class="card"><h3><a href="/collections/{cid}/">{HTML(collection["title"])}</a></h3><p>{HTML(collection.get("description",""))}</p><p>{len(collection["items"])} source files</p></div>')
    home=f'''<section class="hero"><p class="eyebrow">Historical research · Primary source documents</p><h2>Stefano Magaddino and Western New York organized crime</h2><p style="max-width:760px">{HTML(SOURCE['introduction'])}</p><p><a href="/collections/">Explore collections →</a> &nbsp; <a href="/search/">Search the full text →</a></p></section><div class="panel"><h3>About this archive</h3><p>This site organizes government source records and machine-generated OCR transcripts into a navigable, growing historical reference. Original records remain available on Internet Archive. The contributor is not the original author of FBI reports.</p><p><strong>Research and collection contribution:</strong> {HTML(SOURCE['byline'])}. <a href="https://archive.org/details/@joe_augstell">View original uploader profile ↗</a></p></div><h2>Collections</h2><div class="cards">{"".join(collcards)}</div><div class="notice"><strong>OCR accuracy notice:</strong> OCR can mistranscribe typewritten words; verify quotations and factual claims against the linked FBI scans.</div>'''
    write('index.html',page('Home',home,description='Searchable historical FBI documents relating to Stefano Magaddino; documents compiled and contributed by Joseph Augstell.'))
    write('collections/index.html',page('Collections','<section class="hero"><h2>Collections</h2><p>New collections, including court and trial records, can be added here later.</p></section><div class="cards">'+''.join(collcards)+'</div>'))
    # Shard a compact inverted word-to-pages index by initial char; load only relevant shards in browser.
    for first, mapping in {}.items():pass
    shards=collections.defaultdict(dict)
    for token,ids in index.items():shards[token[0]][token]=ids
    for ch,mapping in shards.items():write('search/index-'+ch+'.json',json.dumps(mapping,separators=(',',':'),ensure_ascii=False))
    write('search/documents.json',json.dumps([{'url':x['url'],'title':x['title']} for x in docs],ensure_ascii=False,separators=(',',':')))
    search_js='''const input=document.querySelector('#query'), button=document.querySelector('#search-button'), result=document.querySelector('#results');const cache={};function tokenize(s){return (s.toLowerCase().match(/[a-z0-9]{3,}/g)||[]).slice(0,8)}async function run(){const words=[...new Set(tokenize(input.value))];if(!words.length){result.textContent='Enter at least three letters or digits.';return}result.textContent='Searching transcripts…';try{const [docs,...postings]=await Promise.all([fetch('/search/documents.json').then(r=>r.json()),...words.map(async w=>{const c=w[0];if(!cache[c])cache[c]=fetch('/search/index-'+c+'.json').then(r=>r.ok?r.json():{});const shard=await cache[c];return shard[w]||[]})]);const matches=postings.reduce((a,b)=>a.filter(x=>b.includes(x)));if(!matches.length){result.textContent='No exact OCR word matches. Try alternate spellings; OCR can misread names.';return}result.innerHTML='<p>'+matches.length+' matching transcript pages or text segments</p>'+matches.slice(0,100).map(id=>'<div class="document"><a href="'+docs[id].url+'">'+docs[id].title.replaceAll('&','&amp;').replaceAll('<','&lt;')+'</a></div>').join('')+(matches.length>100?'<p>Showing first 100 matches. Narrow your search with more words.</p>':'')}catch(e){result.textContent='Search not available in this preview; run the online archive build first.'}}button.addEventListener('click',run);input.addEventListener('keydown',e=>{if(e.key==='Enter')run()});'''
    write('search/search.js',search_js)
    write('search/index.html',page('Search OCR transcripts',f'''<section class="hero"><h2>Search the transcripts</h2><p>Searches exact OCR words across imported collections. For multiword searches, all words must occur within the same OCR page or text segment. This tool runs on your device—no paid server required.</p></section><div class="panel"><div class="toolbar"><input aria-label="Search query" id="query" placeholder="Try Magaddino, Valachi, Buffalo…"><button id="search-button">Search</button></div><div id="results" aria-live="polite">{len(docs)} OCR text pages or segments available in this build.</div></div><p class="muted">Because OCR may misread names, try different spellings and verify all matches against original scans.</p><script src="/search/search.js" defer></script>'''))
    base=args.base_url.rstrip('/')
    write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+HTML(base+p)+'</loc></url>' for p in all_urls)+'</urlset>')
    write('robots.txt','User-agent: *\nAllow: /\nSitemap: '+base+'/sitemap.xml\n')
    write('build-report.json',json.dumps(status,indent=2))
    print('Built',len(docs),'OCR text pages or chunks,',len(all_urls),'URLs into',OUT)
    for row in status:print(row['item'],row['state'],row['ocr_segments'])

if __name__=='__main__':main()
