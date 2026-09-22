from __future__ import annotations
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlsplit, unquote
import subprocess, re, html, shutil, sys, json
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT=Path(__file__).resolve().parents[1]
PAGES=[
 {"path":ROOT/"index.html","url":"https://www.sliderrevolution.com/templates/carousel-design-templates-wordpress-pack/"},
 {"path":ROOT/"korr-artistic-horizontal-portfolio-carousel/index.html","url":"https://www.sliderrevolution.com/templates/korr-artistic-horizontal-portfolio-carousel/"},
 {"path":ROOT/"filmstrip-hero-3d-image-carousel-collection/index.html","url":"https://www.sliderrevolution.com/templates/filmstrip-hero-3d-image-carousel-collection/"},
]
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153 Safari/537.36"
HOSTS={"www.sliderrevolution.com","sliderrevolution.com"}

def curl_bytes(url):
 p=subprocess.run(["curl","-fLsS","--compressed","--retry","3","--retry-all-errors","--connect-timeout","20","--max-time","90","-A",UA,"-e","https://www.sliderrevolution.com/",url],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode:
  raise RuntimeError(p.stderr.decode(errors="ignore")[-1500:])
 return p.stdout

def curl_text(url): return curl_bytes(url).decode(errors="ignore")

def fetch(url,dest,required=True):
 dest.parent.mkdir(parents=True,exist_ok=True)
 try:
  data=curl_bytes(url)
  if not data: raise RuntimeError("empty")
  dest.write_bytes(data)
  print("FETCH",url,"->",dest.relative_to(ROOT),len(data))
  return True
 except Exception as e:
  print("FETCH FAIL",url,e,file=sys.stderr)
  if required: raise
  return False

def absurl(u,base):
 if not u:return None
 u=html.unescape(str(u).strip())
 if u.startswith("//"):u="https:"+u
 return urljoin(base,u)

def local_path_for(url):
 p=urlsplit(url)
 if p.netloc not in HOSTS:return None
 path=unquote(p.path)
 if not path or path=="/":return None
 return path if path.startswith("/") else "/"+path

def ensure_firstparty(url):
 path=local_path_for(url)
 if not path:return None
 dest=ROOT/path.lstrip("/")
 if not dest.exists() or dest.stat().st_size==0:
  fetch(url,dest,required=False)
 return path if dest.exists() else None

def localize_css_file(path:Path,source_url:str):
 try:s=path.read_text(errors="ignore")
 except:return
 changed=False
 for raw in list(dict.fromkeys(re.findall(r'url\(\s*([\'"]?)(.*?)\1\s*\)',s,re.I))):
  u=raw[1].strip()
  if not u or u.startswith(("data:","blob:","#")):continue
  au=absurl(u,source_url)
  lp=ensure_firstparty(au)
  if lp:
   s=s.replace(u,lp);changed=True
 if changed:path.write_text(s)

def clean_fragment(fragment,base):
 # direct-load lazy resources
 for tag in fragment.find_all(True):
  for lazy,real in [("data-lazy-src","src"),("data-src","src"),("data-lazy-srcset","srcset"),("data-srcset","srcset")]:
   if tag.has_attr(lazy):
    tag[real]=tag[lazy]
    del tag[lazy]
  # localise source-like attrs
  for attr in ["src","poster"]:
   if tag.has_attr(attr):
    v=str(tag[attr])
    if v.startswith("data:"):continue
    au=absurl(v,base)
    lp=ensure_firstparty(au)
    if lp:tag[attr]=lp
    elif urlsplit(au).scheme in ("http","https"):tag[attr]="/__sitecloner/blocked"
  for attr in ["srcset"]:
   if tag.has_attr(attr):
    parts=[]
    for part in str(tag[attr]).split(","):
     bits=part.strip().split()
     if not bits:continue
     au=absurl(bits[0],base)
     lp=ensure_firstparty(au)
     bits[0]=lp or "/__sitecloner/blocked"
     parts.append(" ".join(bits))
    tag[attr]=", ".join(parts)
  # anchors: preserve only routes within the three-page static site or same-page anchors.
  if tag.name=="a" and tag.has_attr("href"):
   h=str(tag["href"])
   if h.startswith("#"):pass
   else:
    au=absurl(h,base)
    p=urlsplit(au)
    route=p.path
    allowed={
      "/templates/carousel-design-templates-wordpress-pack/":"/",
      "/templates/korr-artistic-horizontal-portfolio-carousel/":"/korr-artistic-horizontal-portfolio-carousel/",
      "/templates/filmstrip-hero-3d-image-carousel-collection/":"/filmstrip-hero-3d-image-carousel-collection/",
      "/korr-artistic-horizontal-portfolio-carousel/":"/korr-artistic-horizontal-portfolio-carousel/",
      "/filmstrip-hero-3d-image-carousel-collection/":"/filmstrip-hero-3d-image-carousel-collection/",
    }
    tag["href"]=allowed.get(route,"#")
 return fragment


# Cache Slider Revolution REST payloads for every module used by all three pages.
# Some modules lazy-load only at mobile breakpoints or when scrolled into view.
rest_dir=ROOT/"__sitecloner/rest"
rest_dir.mkdir(parents=True,exist_ok=True)
jobs=[]
module_ids=set()
slide_pairs=set()
for item in PAGES:
    src=item["path"].read_text(errors="ignore")
    for mid in re.findall(r'<sr7-module\b[^>]*\bdata-id=["\'](\d+)["\']',src,re.I):
        module_ids.add(mid)
        # Restrict slide IDs to slides nested in the same module by scanning its block.
        mm=re.search(rf'<sr7-module\b[^>]*\bdata-id=["\']{re.escape(mid)}["\'][^>]*>(.*?)</sr7-module>',src,re.I|re.S)
        if mm:
            for sid in re.findall(r'<sr7-slide\b[^>]*\bdata-key=["\'](\d+)["\']',mm.group(1),re.I):
                slide_pairs.add((mid,sid))

def rest_fetch(task):
    mid,sid=task
    if sid:
        url=f"https://www.sliderrevolution.com/wp-json/sliderrevolution/sliders/{mid}?srengine=7&slideid={sid}"
        dest=rest_dir/f"{mid}-{sid}.json"
    else:
        url=f"https://www.sliderrevolution.com/wp-json/sliderrevolution/sliders/{mid}?srengine=7"
        dest=rest_dir/f"{mid}.json"
    ok=fetch(url,dest,required=(sid is None))
    return mid,sid,ok,dest

tasks=[(m,None) for m in sorted(module_ids)] + sorted(slide_pairs)
results=[]
with ThreadPoolExecutor(max_workers=8) as ex:
    futs=[ex.submit(rest_fetch,t) for t in tasks]
    for fut in as_completed(futs):
        results.append(fut.result())

routes={}
for mid,sid,ok,dest in results:
    if not ok or not dest.exists(): continue
    key=f"{mid}:{sid or ''}"
    routes[key]="/"+str(dest.relative_to(ROOT)).replace("\\","/")

rest_router = """(() => {
  const ROUTES = __ROUTES__;
  const mapRest = (u) => {
    try {
      const a = new URL(String(u && u.url ? u.url : u), location.href);
      const m = a.pathname.match(/(?:blocked|wp-json\/)?sliderrevolution\/sliders\/(\d+)/);
      if (!m) return u;
      const mid=m[1], sid=a.searchParams.get('slideid')||'';
      return ROUTES[mid+':'+sid] || ROUTES[mid+':'] || u;
    } catch(e) { return u; }
  };
  const oldFetch=window.fetch&&window.fetch.bind(window);
  if(oldFetch) window.fetch=(u,o)=>oldFetch(mapRest(u),o);
  const oldOpen=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(method,url,...rest){return oldOpen.call(this,method,mapRest(url),...rest)};
})();
""".replace("__ROUTES__",json.dumps(routes,separators=(",",":")))
(ROOT/"__sitecloner/rest-router.js").write_text(rest_router)
print("REST ROUTES",len(routes),"modules",len(module_ids),"slide payloads",len(slide_pairs))


for item in PAGES:
 p=item["path"];base=item["url"]
 current=p.read_text(errors="ignore")
 live=curl_text(base)
 cs=BeautifulSoup(current,"html.parser")
 ls=BeautifulSoup(live,"html.parser")

 # Exact live header/footer DOM, but all resource URLs become same-origin local.
 lh=ls.find("header")
 lf=ls.find("footer")
 if not lh or not lf: raise SystemExit(f"{base}: live header/footer missing")
 lh=clean_fragment(BeautifulSoup(str(lh),"html.parser"),base).find("header")
 lf=clean_fragment(BeautifulSoup(str(lf),"html.parser"),base).find("footer")
 ch=cs.find("header");cf=cs.find("footer")
 if not ch or not cf: raise SystemExit(f"{p}: current header/footer missing")
 ch.replace_with(lh)
 cf.replace_with(lf)

 # Remove our previously approximated stylesheet injection block links.
 for link in list(cs.find_all("link",rel=lambda x:x and "stylesheet" in x)):
  href=str(link.get("href",""))
  if any(x in href for x in [
   "/wp-includes/blocks/navigation/",
   "/wp-content/cache/min/1/wp-content/plugins/essential-grid/",
   "/wp-content/cache/min/1/wp-content/plugins/mega-menu-blocks/",
   "/wp-content/cache/min/1/wp-content/plugins/revslider/",
   "/wp-content/cache/min/1/wp-content/plugins/tp-wp-ajax-search/",
   "/wp-content/cache/background-css/1/www.sliderrevolution.com/",
  ]):
   link.decompose()

 # Download and append the exact current live first-party stylesheet stack, in live order.
 live_links=[]
 for link in ls.find_all("link"):
  rel=" ".join(link.get("rel",[])).lower()
  if "stylesheet" not in rel:continue
  au=absurl(link.get("href"),base)
  if not au or urlsplit(au).netloc not in HOSTS:continue
  lp=ensure_firstparty(au)
  if not lp:continue
  dest=ROOT/lp.lstrip("/")
  localize_css_file(dest,au)
  live_links.append((lp,dict(link.attrs)))

 head=cs.head
 marker=cs.new_tag("meta");marker["name"]="static-live-style-stack";marker["content"]="current live first-party CSS"
 head.append(marker)
 for lp,attrs in live_links:
  tag=cs.new_tag("link")
  for k,v in attrs.items():
   if k=="href":continue
   tag[k]=v
  tag["href"]=lp
  head.append(tag)

 # Append exact live inline CSS last so generated WordPress block/header/footer rules win.
 for st in ls.head.find_all("style"):
  new=BeautifulSoup(str(st),"html.parser").find("style")
  txt=new.string or new.get_text()
  # localise first-party absolute resource URLs inside inline CSS
  urls=re.findall(r'https?://(?:www\.)?sliderrevolution\.com/[^\s\'")]+',txt)
  for u in dict.fromkeys(urls):
   lp=ensure_firstparty(u)
   if lp: txt=txt.replace(u,lp)
  new.string=txt
  head.append(new)

 # Restore live body classes: theme selectors depend on these.
 if ls.body and cs.body:
  cs.body["class"]=ls.body.get("class",[])
  if ls.body.has_attr("style"):cs.body["style"]=ls.body["style"]

 # Localise remaining Slider Revolution font URLs in the full document.
 out=str(cs)
 font_urls=re.findall(r'https?://(?:www\.)?sliderrevolution\.com(/wp-content/uploads/themepunch/gfonts/[A-Za-z0-9_./%+\-]+)',out,re.I)
 for path in dict.fromkeys(font_urls):
  url="https://www.sliderrevolution.com"+path
  fetch(url,ROOT/path.lstrip("/"),required=False)
  if (ROOT/path.lstrip("/")).exists():
   out=out.replace(url,path).replace("http://www.sliderrevolution.com"+path,path)

 p.write_text(out)
 print("REPAIRED",p.relative_to(ROOT),"styles",len(live_links))

(ROOT/"FULL_PAGE_REPAIR.txt").write_text(
"""FULL PAGE REPAIR

Replaced each static page header and footer with the exact current live DOM.
Downloaded and linked the exact current first-party WordPress stylesheet stack.
Appended current live WordPress inline style blocks for block/theme parity.
Restored live body classes used by WordPress selectors.
Localised header/footer images and responsive sources.
Retained the already-working local Slider Revolution runtime and local REST bridge.
All outbound image/resource URLs in the replaced chrome are local or blocked.
"""
)
