from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
from html.parser import HTMLParser
import html, json, re, shutil, sys, urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.bootstrap' / 'asset-manifest.tsv'
BLOCKED = '/__sitecloner/blocked'
TEXT_EXTS = {'.html','.css','.js','.json','.xml','.svg','.txt','.map'}
PAGE_ROUTES = {
    'index.html': '/',
    'korr-artistic-horizontal-portfolio-carousel/index.html': '/korr-artistic-horizontal-portfolio-carousel/',
    'filmstrip-hero-3d-image-carousel-collection/index.html': '/filmstrip-hero-3d-image-carousel-collection/',
}

pairs=[]
for line in MANIFEST.read_text().splitlines():
    if not line.strip(): continue
    u,p=line.split('\t',1)
    pairs.append((u,'/'+p.lstrip('/')))
MAP=dict(pairs)

sitecloner=ROOT/'__sitecloner'
sitecloner.mkdir(exist_ok=True)
(sitecloner/'empty.js').write_text('/* local no-op */\n')
(sitecloner/'empty.css').write_text('/* local no-op */\n')
(sitecloner/'blocked').write_bytes(b'')

runtime = r'''const M=__MAP__;
const BLOCKED='/__sitecloner/blocked';
const STRICT=true;
(()=>{
const map=u=>{try{const raw=String(u&&u.url?u.url:u);if(!raw||raw.startsWith('data:')||raw.startsWith('blob:')||raw.startsWith('about:')||raw.startsWith('#'))return raw;const a=new URL(raw,location.href);if(M[a.href])return M[a.href];if(a.origin===location.origin)return raw;if(['http:','https:','ws:','wss:'].includes(a.protocol))return STRICT?BLOCKED:raw;return raw}catch(e){return STRICT?BLOCKED:u}};
window.__LOCAL_ONLY_MAP__=map;
const F=window.fetch;window.fetch=(u,o)=>F.call(window,map(u),o);
const O=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u,...r){return O.call(this,m,map(u),...r)};
try{const W=window.WebSocket;window.WebSocket=function(u,p){const x=map(u);if(x===BLOCKED)throw new DOMException('Blocked by local-only firewall','SecurityError');return new W(x,p)}}catch(e){}
try{const E=window.EventSource;window.EventSource=function(u,o){const x=map(u);if(x===BLOCKED)throw new DOMException('Blocked by local-only firewall','SecurityError');return new E(x,o)}}catch(e){}
try{const B=navigator.sendBeacon?.bind(navigator);if(B)navigator.sendBeacon=(u,d)=>{const x=map(u);return x===BLOCKED?false:B(x,d)}}catch(e){}
for(const [C,p] of [[HTMLImageElement,'src'],[HTMLScriptElement,'src'],[HTMLLinkElement,'href'],[HTMLVideoElement,'src'],[HTMLAudioElement,'src'],[HTMLSourceElement,'src'],[HTMLIFrameElement,'src']]){try{const q=Object.getOwnPropertyDescriptor(C.prototype,p);if(q&&q.set)Object.defineProperty(C.prototype,p,{...q,set(v){return q.set.call(this,map(v))}})}catch(e){}}
const SA=Element.prototype.setAttribute;Element.prototype.setAttribute=function(n,v){if(['src','href','data','action','poster'].includes(String(n).toLowerCase()))v=map(v);return SA.call(this,n,v)};
document.addEventListener('click',e=>{const a=e.target&&e.target.closest?e.target.closest('a[href]'):null;if(!a)return;const x=map(a.href);if(x===BLOCKED){e.preventDefault();e.stopPropagation()}else if(x!==a.href)a.href=x},true);
})();
'''.replace('__MAP__', json.dumps(MAP,separators=(',',':')))
(sitecloner/'runtime.js').write_text(runtime)

SPECIAL={
 'https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js':'/__external__/ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js',
 'https://player.vimeo.com/api/player.js':'/__external__/player.vimeo.com/api/player.js',
 'https://www.youtube.com/iframe_api':'/__sitecloner/empty.js',
 'https://static.ads-twitter.com/uwt.js':'/__sitecloner/empty.js',
 'https://www.redditstatic.com/ads/pixel.js':'/__sitecloner/empty.js',
 'https://bzrcdn.openai.com/sdk/oaiq.min.js':'/__sitecloner/empty.js',
 'https://static.cloudflareinsights.com':'/__sitecloner/blocked',
}

repls=sorted(pairs,key=lambda x:len(x[0]),reverse=True)
for p in ROOT.rglob('*'):
    if not p.is_file() or '.git' in p.parts or '.bootstrap' in p.parts or '.github' in p.parts: continue
    if p.suffix.lower() not in TEXT_EXTS: continue
    try: s=p.read_text(errors='ignore')
    except Exception: continue
    orig=s
    for u,local in repls:
        s=s.replace(u,local).replace(html.escape(u,quote=True),local)
        s=s.replace(u.replace('/','\\/'),local.replace('/','\\/'))
    for u,local in SPECIAL.items(): s=s.replace(u,local)
    s=s.replace('https://www.sliderrevolution.com/wp-admin/admin-ajax.php',BLOCKED)
    s=s.replace('https://www.sliderrevolution.com/wp-json/',BLOCKED)
    s=s.replace('https:\\/\\/www.sliderrevolution.com\\/wp-admin\\/admin-ajax.php',BLOCKED)
    s=s.replace('https:\\/\\/www.sliderrevolution.com\\/wp-json\\/',BLOCKED)
    s=s.replace('https://www.sliderrevolution.com','').replace('http://www.sliderrevolution.com','')
    s=s.replace('https:\\/\\/www.sliderrevolution.com','').replace('http:\\/\\/www.sliderrevolution.com','')
    if s!=orig: p.write_text(s)

fa=ROOT/'wp-content/plugins/revslider/public/css/fonts/font-awesome/fonts'
if fa.exists():
    for ext in ['woff2','woff','ttf','eot','svg']:
        plain=fa/f'fontawesome-webfont.{ext}'
        if not plain.exists():
            cand=next(iter(sorted(fa.glob(f'fontawesome-webfont__q_*.{ext}'))),None)
            if cand: shutil.copy2(cand,plain)

CSP="default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline' data: blob:; img-src 'self' data: blob:; font-src 'self' data: blob:; media-src 'self' data: blob:; connect-src 'self' data: blob:; worker-src 'self' blob:; child-src 'self' blob:; frame-src 'self' about: blob:; object-src 'self' data: blob:; form-action 'self'; base-uri 'self'; navigate-to 'self'"

for rel,route in PAGE_ROUTES.items():
    p=ROOT/rel
    s=p.read_text(errors='ignore')
    s=re.sub(r'<!-- Google Tag Manager -->.*?<!-- End Google Tag Manager -->','',s,flags=re.S|re.I)
    s=re.sub(r'<script[^>]*>[^<]*google_tags_first_party.*?</script>','',s,flags=re.S|re.I)
    s=re.sub(r'<script[^>]*>.*?googletagmanager\.com/gtm\.js.*?</script>','',s,flags=re.S|re.I)
    s=re.sub(r'<script[^>]*>.*?oaiq\([\'\"]init[\'\"].*?</script>','',s,flags=re.S|re.I)
    s=re.sub(r'<script[^>]*class=[\'\"]yoast-schema-graph[\'\"][^>]*>.*?</script>','',s,flags=re.S|re.I)
    s=re.sub(r'<script[^>]+src=[\'\"][^\'\"]*(?:googletagmanager|google-analytics|ads-twitter|redditstatic|cloudflareinsights|bzrcdn\.openai)[^\'\"]*[\'\"][^>]*>\s*</script>','',s,flags=re.S|re.I)
    s=re.sub(r'(<link[^>]+rel=[\'\"]canonical[\'\"][^>]+href=[\'\"])[^\'\"]*([\'\"])',r'\1'+route+r'\2',s,flags=re.I)
    s=re.sub(r'(<meta[^>]+property=[\'\"]og:url[\'\"][^>]+content=[\'\"])[^\'\"]*([\'\"])',r'\1'+route+r'\2',s,flags=re.I)
    def attr_fix(m):
        pre,val,quote=m.group(1),html.unescape(m.group(2)),m.group(3)
        if not re.match(r'^(?:https?:)?//',val,re.I): return m.group(0)
        if val in MAP: return pre + MAP[val] + quote
        return pre + BLOCKED + quote
    s=re.sub(r'((?:src|href|poster|action|data-src|data-lazy-src|data-bg|data-thumb)\s*=\s*[\'\"])([^\'\"]+)([\'\"])',attr_fix,s,flags=re.I)
    s=re.sub(r'<meta[^>]+http-equiv=[\'\"]Content-Security-Policy[\'\"][^>]*>','',s,flags=re.I)
    s=re.sub(r'<script[^>]+src=[\'\"]/__sitecloner/runtime\.js[\'\"][^>]*>\s*</script>','',s,flags=re.I)
    inject=f'<meta http-equiv="Content-Security-Policy" content="{CSP}"><script src="/__sitecloner/runtime.js"></script>'
    s=re.sub(r'<head\s*>','<head>'+inject,s,count=1,flags=re.I)
    p.write_text(s)

(ROOT/'vercel.json').write_text(json.dumps({
  'cleanUrls':True,'trailingSlash':True,
  'headers':[{'source':'/(.*)','headers':[
    {'key':'X-Content-Type-Options','value':'nosniff'},
    {'key':'Referrer-Policy','value':'no-referrer'},
    {'key':'Permissions-Policy','value':'geolocation=(), microphone=(), camera=()'}]}]
},indent=2)+'\n')

# Fetch first-party static resources newly referenced by the current page HTML.
# This is build-time only. The finished mirror has no live-site fallback.
STATIC_EXTS = {'.css','.js','.png','.jpg','.jpeg','.webp','.gif','.svg','.ico','.woff','.woff2','.ttf','.otf','.eot','.mp4','.webm','.json'}
for rel in PAGE_ROUTES:
    page = ROOT / rel
    source = page.read_text(errors='ignore')
    candidates = set()
    candidates.add('/wp-content/uploads/2026/06/template-preview-1-300x169.jpg')
    for attrval in re.findall(r"(?:src|href|poster|data-src|data-lazy-src|data-bg|data-thumb)\s*=\s*['\"]([^'\"]+)", source, re.I):
        val = html.unescape(attrval).split('#',1)[0].split('?',1)[0]
        if not val.startswith('/') or val.startswith('/__sitecloner/'):
            continue
        if Path(val).suffix.lower() not in STATIC_EXTS:
            continue
        dest = ROOT / val.lstrip('/')
        if not dest.exists():
            candidates.add(val)
    for val in sorted(candidates):
        dest = ROOT / val.lstrip('/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            'https://www.sliderrevolution.com' + val,
            headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.sliderrevolution.com/'}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if data:
                dest.write_bytes(data)
                print('Fetched newly referenced local asset', val)
        except Exception as e:
            print('Could not fetch newly referenced asset', val, e, file=sys.stderr)

URL_ATTRS={'src','href','poster','action','data-src','data-lazy-src','data-bg','data-thumb','srcset','data-srcset'}
external=[]; missing=[]; html_refs=0

def check_html_url(source,tag,attr,u):
    global html_refs
    if not u or u.startswith(('data:','blob:','about:','mailto:','tel:','javascript:','#')): return
    html_refs+=1
    if re.match(r'^(?:https?:)?//',u,re.I): external.append((source,tag,attr,u)); return
    if tag=='a' or (tag=='link' and attr=='href' and not re.search(r'\.(?:css|js|png|jpe?g|webp|gif|svg|ico|woff2?|ttf|otf|eot)(?:[?#]|$)',u,re.I)): return
    path=u.split('#',1)[0].split('?',1)[0]
    if not path or path=='/': return
    f=(ROOT/path.lstrip('/')) if path.startswith('/') else (Path(source).parent/path)
    if path.endswith('/'): f=f/'index.html'
    if not f.exists(): missing.append((source,tag,attr,u))

class P(HTMLParser):
    def __init__(self, source): super().__init__(convert_charrefs=True); self.source=source
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if not v or k.lower() not in URL_ATTRS: continue
            vals=[x.strip().split()[0] for x in v.split(',') if x.strip()] if 'srcset' in k.lower() else [v]
            for u in vals: check_html_url(self.source,tag,k,u)

for rel in PAGE_ROUTES:
    p=ROOT/rel; parser=P(rel); parser.feed(p.read_text(errors='ignore'))

css_refs=0; css_external=[]; css_missing=[]
for p in ROOT.rglob('*.css'):
    s=p.read_text(errors='ignore')
    for u in re.findall(r'url\(\s*[\'\"]?([^\'\")]+)',s,re.I):
        u=u.strip()
        if not u or u.startswith(('data:','blob:','#')): continue
        css_refs+=1
        if re.match(r'^(?:https?:)?//',u,re.I): css_external.append((str(p.relative_to(ROOT)),u)); continue
        q=u.split('#',1)[0].split('?',1)[0]
        f=(ROOT/q.lstrip('/')) if q.startswith('/') else (p.parent/q).resolve()
        if not f.exists(): css_missing.append((str(p.relative_to(ROOT)),u))

dyn=[]
patterns=[r'fetch\s*\(\s*[\'\"]https?://',r'\.open\s*\([^,]+,\s*[\'\"]https?://',r'sendBeacon\s*\(\s*[\'\"]https?://',r'new\s+WebSocket\s*\(\s*[\'\"]wss?://',r'new\s+EventSource\s*\(\s*[\'\"]https?://',r'\.src\s*=\s*[\'\"]https?://']
for p in list(ROOT.rglob('*.js'))+[ROOT/x for x in PAGE_ROUTES]:
    if p==sitecloner/'runtime.js' or '.bootstrap' in p.parts: continue
    s=p.read_text(errors='ignore')
    for pat in patterns:
        if re.search(pat,s,re.I): dyn.append((str(p.relative_to(ROOT)),pat))

audit=f'''LOCALIZATION AUDIT

Primary routes
/
/korr-artistic-horizontal-portfolio-carousel/
/filmstrip-hero-3d-image-carousel-collection/

Checks
HTML resource references checked: {html_refs}
External HTML resource/navigation URLs: {len(external)}
Missing HTML resources: {len(missing)}
CSS asset references checked: {css_refs}
External CSS URLs: {len(css_external)}
Missing CSS assets: {len(css_missing)}
Direct executable remote call patterns: {len(dyn)}

Protections
All captured runtime assets resolve to local repository paths.
Content Security Policy restricts network activity to the local origin.
The browser-side local-only firewall blocks unknown outbound HTTP, HTTPS, WS and WSS activity.
Analytics and advertising bootstraps are removed or neutralized.
'''
(ROOT/'LOCALIZATION_AUDIT.txt').write_text(audit)
(ROOT/'README.md').write_text('''# SR local-only three page build

Routes:

* `/`
* `/korr-artistic-horizontal-portfolio-carousel/`
* `/filmstrip-hero-3d-image-carousel-collection/`

All runtime assets are stored in this repository and served from the same origin. Outbound network activity is blocked by CSP and the local-only runtime firewall. See `LOCALIZATION_AUDIT.txt` for the verification summary.
''')
print(audit)
if external or missing or css_external or css_missing or dyn:
    print('External:',external[:20],file=sys.stderr)
    print('Missing:',missing[:20],file=sys.stderr)
    print('CSS external:',css_external[:20],file=sys.stderr)
    print('CSS missing:',css_missing[:20],file=sys.stderr)
    print('Dynamic:',dyn[:20],file=sys.stderr)
    raise SystemExit(3)
