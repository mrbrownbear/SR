from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit, unquote
import subprocess, re, html, shutil, sys

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    {
        "path": ROOT / "index.html",
        "url": "https://www.sliderrevolution.com/templates/carousel-design-templates-wordpress-pack/",
        "title": "Carousel Design Templates – Premium WordPress Pack",
        "theme_q": "4963683af3",
    },
    {
        "path": ROOT / "korr-artistic-horizontal-portfolio-carousel/index.html",
        "url": "https://www.sliderrevolution.com/templates/korr-artistic-horizontal-portfolio-carousel/",
        "title": "Korr – Artistic Horizontal Portfolio Carousel",
        "theme_q": "8c121fc0f3",
    },
    {
        "path": ROOT / "filmstrip-hero-3d-image-carousel-collection/index.html",
        "url": "https://www.sliderrevolution.com/templates/filmstrip-hero-3d-image-carousel-collection/",
        "title": "Filmstrip Hero – 3D Image Carousel Collection",
        "theme_q": "22d3f5e36e",
    },
]

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
REFERER="https://www.sliderrevolution.com/"

def fetch_bytes(url: str) -> bytes:
    p=subprocess.run([
        "curl","-fLsS","--compressed","--retry","3","--retry-all-errors",
        "--connect-timeout","20","--max-time","90",
        "-A",UA,"-e",REFERER,url
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="ignore")[-1200:])
    return p.stdout

def fetch_to(url: str, dest: Path, required=False) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        data=fetch_bytes(url)
        if not data:
            raise RuntimeError("empty response")
        dest.write_bytes(data)
        print("FETCHED", url, "->", dest.relative_to(ROOT), len(data))
        return True
    except Exception as e:
        print("FETCH FAIL",url,e,file=sys.stderr)
        if required:
            raise
        return False

def copy_alias(src: str, dest: str, required=True):
    a=ROOT/src
    b=ROOT/dest
    if not a.exists():
        if required:
            raise FileNotFoundError(a)
        return
    b.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(a,b)
    print("ALIAS",src,"->",dest)

# Exact runtime aliases Slider Revolution constructs itself.
copy_alias("wp-content/cache/min/1/wp-content/plugins/revslider/public/css/sr7__q_5dad1e3577.css",
           "wp-content/plugins/revslider/public/css/sr7.css")
copy_alias("wp-content/cache/min/1/wp-content/plugins/revslider/public/js/sr7__q_5dad1e3577.js",
           "wp-content/plugins/revslider/public/js/sr7.js")
copy_alias("wp-content/cache/min/1/wp-content/plugins/revslider/public/js/libs/tptools__q_5dad1e3577.js",
           "wp-content/plugins/revslider/public/js/libs/tptools.js")
copy_alias("wp-content/plugins/revslider/public/css/sr7.lp__q_3454752323.css",
           "wp-content/plugins/revslider/public/css/sr7.lp.css")
copy_alias("wp-content/plugins/revslider/public/css/sr7.media__q_3454752323.css",
           "wp-content/plugins/revslider/public/css/sr7.media.css")
copy_alias("wp-content/plugins/revslider/public/js/libs/webgl__q_3454752323.js",
           "wp-content/plugins/revslider/public/js/libs/webgl.js")
copy_alias("wp-content/plugins/revslider/public/js/libs/effects__q_3454752323.js",
           "wp-content/plugins/revslider/public/js/libs/effects.js")

# Resources that were not present in the original capture but are generated dynamically.
OPTIONAL_RESOURCES = [
    ("wp-content/plugins/revslider/public/js/libs/three.js", "https://www.sliderrevolution.com/wp-content/plugins/revslider/public/js/libs/three.js?ver=7.2.0"),
    ("wp-content/plugins/revslider/public/css/sr7.btns.css", "https://www.sliderrevolution.com/wp-content/plugins/revslider/public/css/sr7.btns.css?ver=7.2.0"),
    ("wp-content/plugins/revslider/public/css/sr7.filters.css", "https://www.sliderrevolution.com/wp-content/plugins/revslider/public/css/sr7.filters.css?ver=7.2.0"),
    ("wp-content/plugins/revslider/public/css/sr7.nav.css", "https://www.sliderrevolution.com/wp-content/plugins/revslider/public/css/sr7.nav.css?ver=7.2.0"),
]
for rel,url in OPTIONAL_RESOURCES:
    if not fetch_to(url,ROOT/rel,required=False):
        # A missing optional CSS must still resolve locally. JS THREE is left absent only if unused.
        if rel.endswith(".css"):
            (ROOT/rel).write_text("/* optional SR7 resource: local no-op */\n")


# Filmstrip lazily asks WordPress REST for slide details. Cache every slide response
# and route those XHR/fetch calls to static JSON files at runtime.
filmstrip_html=(ROOT/"filmstrip-hero-3d-image-carousel-collection/index.html").read_text(errors="ignore")
filmstrip_ids=sorted(set(re.findall(r'<sr7-slide\b[^>]*\bdata-key=["\'](\d+)["\']',filmstrip_html,re.I)))
rest_dir=ROOT/"__sitecloner/rest"
rest_dir.mkdir(parents=True,exist_ok=True)
for sid in filmstrip_ids:
    url=f"https://www.sliderrevolution.com/wp-json/sliderrevolution/sliders/3538?srengine=7&slideid={sid}"
    fetch_to(url,rest_dir/f"3538-{sid}.json",required=True)

rest_router = r"""(() => {
  const mapRest = (u) => {
    try {
      const a = new URL(String(u && u.url ? u.url : u), location.href);
      const isFilmstrip =
        a.pathname.includes('/__sitecloner/blockedsliderrevolution/sliders/3538') ||
        a.pathname.includes('/wp-json/sliderrevolution/sliders/3538') ||
        a.pathname.includes('/__sitecloner/rest/sliderrevolution/sliders/3538');
      if (isFilmstrip) {
        const sid = a.searchParams.get('slideid');
        if (sid) return '/__sitecloner/rest/3538-' + sid + '.json';
      }
    } catch (e) {}
    return u;
  };

  const oldFetch = window.fetch && window.fetch.bind(window);
  if (oldFetch) {
    window.fetch = (u, o) => oldFetch(mapRest(u), o);
  }

  const oldOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    return oldOpen.call(this, method, mapRest(url), ...rest);
  };
})();
"""
(ROOT/"__sitecloner/rest-router.js").write_text(rest_router)

CORE_SCRIPTS = """
<!-- STATIC_RUNTIME_CORE_BEGIN -->
<link rel="stylesheet" href="/wp-includes/blocks/navigation/style.min__q_aab5badeb3.css" id="wp-block-navigation-css">
<link rel="stylesheet" href="/wp-content/cache/min/1/wp-content/plugins/mega-menu-blocks/front/assets/css/tp-megamenu__q_5dad1e3577.css" id="tp-megamenu-css">
<link rel="stylesheet" href="/wp-content/cache/min/1/wp-content/plugins/revslider/public/css/sr7__q_5dad1e3577.css" id="sr7css-css">
<script src="/wp-includes/js/jquery/jquery.min__q_c8a53ae4de.js" id="jquery-core-js"></script>
<script src="/wp-includes/js/jquery/jquery-migrate.min__q_ed1ec5e4c7.js" id="jquery-migrate-js"></script>
<script src="/wp-content/cache/min/1/wp-content/plugins/mega-menu-blocks/front/assets/js/tpgsap__q_5dad1e3577.js" id="tpgsap-js"></script>
<script src="/wp-content/cache/min/1/wp-content/plugins/revslider/public/js/libs/tptools__q_5dad1e3577.js" id="tp-tools-js"></script>
<script src="/wp-content/cache/min/1/wp-content/plugins/revslider/public/js/sr7__q_5dad1e3577.js" id="sr7-js"></script>
<script src="/__sitecloner/rest-router.js" id="static-rest-router"></script>
<script defer src="/wp-content/cache/min/1/wp-content/plugins/mega-menu-blocks/front/assets/js/tp-megamenu__q_5dad1e3577.js" id="tp-megamenu-js"></script>
<script defer src="/wp-content/cache/min/1/wp-content/plugins/tp-wp-ajax-search/front/assets/js/ajax-search__q_5dad1e3577.js" id="tp-ajax-search-js"></script>
<!-- STATIC_RUNTIME_CORE_END -->
"""

def localize_firstparty_url(url: str) -> str | None:
    u=html.unescape(url or "").strip()
    if u.startswith("//"):
        u="https:"+u
    if u.startswith("/"):
        return u
    if not u.startswith(("http://","https://")):
        return None
    parts=urlsplit(u)
    if parts.netloc not in {"www.sliderrevolution.com","sliderrevolution.com"}:
        return None
    path=unquote(parts.path)
    if not path.startswith("/"):
        path="/"+path
    dest=ROOT/path.lstrip("/")
    if not dest.exists() or dest.stat().st_size==0:
        fetch_to(u,dest,required=False)
    return path if dest.exists() else None

def replace_blocked_images(current: str, live: str) -> str:
    if BeautifulSoup is None:
        return current
    live_soup=BeautifulSoup(live,"html.parser")
    live_imgs=live_soup.find_all("img")
    idx=0
    repaired=0
    def repl(m):
        nonlocal idx,repaired
        tag=m.group(0)
        li=live_imgs[idx] if idx < len(live_imgs) else None
        idx += 1
        if "/__sitecloner/blocked" not in tag or li is None:
            return tag
        candidates=[
            li.get("data-lazy-src"),
            li.get("data-src"),
            li.get("src"),
        ]
        chosen=None
        for c in candidates:
            if not c or c.startswith("data:"):
                continue
            loc=localize_firstparty_url(c)
            if loc:
                chosen=loc
                break
        if chosen:
            tag=re.sub(r'(\bsrc\s*=\s*)(["\'])/__sitecloner/blocked\2',
                       lambda x:x.group(1)+x.group(2)+chosen+x.group(2),
                       tag,count=1,flags=re.I)
            repaired+=1
        return tag
    out=re.sub(r'<img\b[^>]*>',repl,current,flags=re.I|re.S)
    print("blocked img repair",repaired,"of",idx,"images; live",len(live_imgs))
    return out

FONT_RE = re.compile(r'https?://(?:www\.)?sliderrevolution\.com(/wp-content/uploads/themepunch/gfonts/[A-Za-z0-9_./%+\-]+)',re.I)

def localize_fonts(s: str) -> str:
    urls=set(m.group(0) for m in FONT_RE.finditer(s))
    for u in sorted(urls):
        path=urlsplit(u).path
        fetch_to(u,ROOT/path.lstrip("/"),required=False)
        if (ROOT/path.lstrip("/")).exists():
            s=s.replace(u,path)
    # protocol-relative forms
    s=re.sub(r'//(?:www\.)?sliderrevolution\.com(/wp-content/uploads/themepunch/gfonts/[A-Za-z0-9_./%+\-]+)',r'\1',s,flags=re.I)
    return s

for item in PAGES:
    p=item["path"]
    s=p.read_text(errors="ignore")
    live=fetch_bytes(item["url"]).decode(errors="ignore")

    # Remove an older reconstruction block if rerun.
    s=re.sub(r'<!-- STATIC_RUNTIME_CORE_BEGIN -->.*?<!-- STATIC_RUNTIME_CORE_END -->','',s,flags=re.S)
    # Restore title.
    if re.search(r'<title\b',s,re.I):
        s=re.sub(r'<title\b[^>]*>.*?</title>',f'<title>{html.escape(item["title"])}</title>',s,count=1,flags=re.I|re.S)
    else:
        s=s.replace("</head>",f"<title>{html.escape(item['title'])}</title></head>",1)

    # Chrome does not support navigate-to; keep the rest of the local-only CSP.
    s=s.replace("; navigate-to 'self'","")

    # Inject all critical local CSS and engine scripts at the beginning of head.
    theme_q=item["theme_q"]
    theme_links=f"""
<link rel="stylesheet" href="/wp-content/cache/background-css/1/www.sliderrevolution.com/wp-content/cache/min/1/wp-content/themes/jadro/style__q_{theme_q}.css" id="jadro-style-css">
<link rel="stylesheet" href="/wp-content/cache/background-css/1/www.sliderrevolution.com/wp-content/cache/min/1/wp-content/plugins/essential-grid/public/assets/css/settings__q_{theme_q}.css" id="esg-plugin-settings-css">
"""
    core=CORE_SCRIPTS.replace("<!-- STATIC_RUNTIME_CORE_END -->",theme_links+"<!-- STATIC_RUNTIME_CORE_END -->")
    s=re.sub(r'(<head\b[^>]*>)',lambda m:m.group(1)+core,s,count=1,flags=re.I)

    # The original page processor used protocol-relative core URLs. Point them to the
    # exact local alias so no runtime mapper is needed for Slider Revolution itself.
    s=s.replace(r"\/\/www.sliderrevolution.com\/wp-content\/plugins\/revslider\/public\/js\/sr7.js",
                r"\/wp-content\/plugins\/revslider\/public\/js\/sr7.js")
    s=s.replace("//www.sliderrevolution.com/wp-content/plugins/revslider/public/js/sr7.js",
                "/wp-content/plugins/revslider/public/js/sr7.js")

    # Recover first-party img sources that the earlier strict pass replaced with blocked.
    s=replace_blocked_images(s,live)

    # Localise every captured Slider Revolution font used by this page.
    s=localize_fonts(s)

    p.write_text(s)

# Also localise first-party font URLs inside stored CSS.
for css in ROOT.rglob("*.css"):
    if ".git" in css.parts:
        continue
    try:
        s=css.read_text(errors="ignore")
    except Exception:
        continue
    n=localize_fonts(s)
    if n!=s:
        css.write_text(n)

# Lightweight static assertions.
for item in PAGES:
    s=item["path"].read_text(errors="ignore")
    must=[
        "/wp-includes/js/jquery/jquery.min__q_c8a53ae4de.js",
        "/wp-content/cache/min/1/wp-content/plugins/revslider/public/js/libs/tptools__q_5dad1e3577.js",
        "/wp-content/cache/min/1/wp-content/plugins/revslider/public/js/sr7__q_5dad1e3577.js",
        "/wp-content/cache/min/1/wp-content/plugins/revslider/public/css/sr7__q_5dad1e3577.css",
    ]
    for x in must:
        if x not in s:
            raise SystemExit(f"{item['path']}: missing required runtime reference {x}")
    if "jQuery is not defined" in s:
        raise SystemExit("unexpected literal error text")
    if "http://www.sliderrevolution.com/wp-content/uploads/themepunch/gfonts/" in s or "https://www.sliderrevolution.com/wp-content/uploads/themepunch/gfonts/" in s:
        raise SystemExit(f"{item['path']}: remote font URL remains")

(ROOT/"STATIC_RUNTIME_REBUILD.txt").write_text(
"""STATIC RUNTIME REBUILD

Restored synchronous local jQuery.
Restored Slider Revolution tptools and sr7 engine scripts.
Restored Slider Revolution, theme, navigation and menu stylesheets.
Created exact local aliases for dynamically constructed SR7 resource paths.
Localised Slider Revolution font files.
Recovered first-party image sources previously replaced by the blocking placeholder.
Runtime verification is performed by a headless Chromium job before commit.
"""
)
