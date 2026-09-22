from pathlib import Path
from bs4 import BeautifulSoup
import subprocess, re, json, html
from urllib.parse import urljoin, urlsplit

ROOT=Path(__file__).resolve().parents[1]
PAGES=[
 ("index.html","https://www.sliderrevolution.com/templates/carousel-design-templates-wordpress-pack/"),
 ("korr-artistic-horizontal-portfolio-carousel/index.html","https://www.sliderrevolution.com/templates/korr-artistic-horizontal-portfolio-carousel/"),
 ("filmstrip-hero-3d-image-carousel-collection/index.html","https://www.sliderrevolution.com/templates/filmstrip-hero-3d-image-carousel-collection/"),
]
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"

def curl(url):
 p=subprocess.run(["curl","-fLsS","--compressed","-A",UA,url],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode: raise SystemExit(p.stderr.decode(errors="ignore"))
 return p.stdout.decode(errors="ignore")

def norm(u,base):
 if not u:return None
 u=html.unescape(u.strip())
 if u.startswith("//"):u="https:"+u
 return urljoin(base,u)

def classify(soup,base):
 out={"css":[],"js":[],"img":[],"fontpreload":[]}
 for x in soup.find_all("link"):
  rel=" ".join(x.get("rel",[])).lower()
  href=norm(x.get("href"),base)
  if not href: continue
  if "stylesheet" in rel: out["css"].append(href)
  if "preload" in rel and x.get("as")=="font": out["fontpreload"].append(href)
 for x in soup.find_all("script"):
  src=norm(x.get("src"),base)
  if src: out["js"].append(src)
 for x in soup.find_all("img"):
  for a in ("src","data-src","data-lazy-src"):
   u=norm(x.get(a),base)
   if u and not u.startswith("data:"):out["img"].append(u)
 return {k:list(dict.fromkeys(v)) for k,v in out.items()}

for rel,url in PAGES:
 live=curl(url)
 cur=(ROOT/rel).read_text(errors="ignore")
 L=classify(BeautifulSoup(live,"html.parser"),url)
 C=classify(BeautifulSoup(cur,"html.parser"),"http://local.test/"+rel)
 print("\n###",rel)
 for k in ("css","js","fontpreload"):
  live_paths=[urlsplit(x).path + (("?" + urlsplit(x).query) if urlsplit(x).query else "") for x in L[k]
              if urlsplit(x).netloc in ("www.sliderrevolution.com","sliderrevolution.com")]
  cur_paths=[urlsplit(x).path + (("?" + urlsplit(x).query) if urlsplit(x).query else "") for x in C[k]]
  missing=[x for x in live_paths if x not in cur_paths]
  print(k,"LIVE",len(live_paths),"CURRENT",len(cur_paths),"MISSING",len(missing))
  for x in missing: print(" MISSING",k,x)

 # page-structure comparison
 for sel in ["header","footer",".wp-site-blocks",".topbar",".menubar",".tp-megamenu-mobile-block"]:
  print("STRUCT",sel,"live",len(BeautifulSoup(live,"html.parser").select(sel)),
        "current",len(BeautifulSoup(cur,"html.parser").select(sel)))
