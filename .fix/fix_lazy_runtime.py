from pathlib import Path
import re, html, json

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    ROOT / "index.html",
    ROOT / "korr-artistic-horizontal-portfolio-carousel/index.html",
    ROOT / "filmstrip-hero-3d-image-carousel-collection/index.html",
]

def replace_lazy_attr(s, attr, real_attr):
    # If the real attribute already exists, replace its value with the lazy local value.
    pat = re.compile(rf'(<[^>]+?)\s{attr}=(["\'])(.*?)\2', re.I | re.S)
    def repl(m):
        whole = m.group(0)
        prefix = m.group(1)
        quote = m.group(2)
        val = html.unescape(m.group(3))
        real_pat = re.compile(rf'\s{real_attr}=(["\'])(.*?)\1', re.I | re.S)
        if real_pat.search(prefix):
            prefix = real_pat.sub(lambda x: f' {real_attr}={x.group(1)}{val}{x.group(1)}', prefix)
        else:
            prefix += f' {real_attr}={quote}{val}{quote}'
        return prefix
    return pat.sub(repl, s)

for p in PAGES:
    s = p.read_text(errors="ignore")
    before = s

    # Make WP Rocket lazy resources eager/local so visual rendering does not depend on its runtime.
    s = replace_lazy_attr(s, "data-lazy-src", "src")
    s = replace_lazy_attr(s, "data-lazy-srcset", "srcset")
    s = replace_lazy_attr(s, "data-lazy-sizes", "sizes")

    # Common lazy iframe/video source attributes from the capture.
    s = replace_lazy_attr(s, "data-src", "src")

    # Remove the captured WP Rocket lazy loader; resources are now direct.
    s = re.sub(
        r'<script[^>]+src=["\'][^"\']*/wp-content/plugins/wp-rocket/assets/js/lazyload/[^"\']+["\'][^>]*>\s*</script>',
        '',
        s,
        flags=re.I | re.S,
    )

    # Remove Rocket's no-JS rule which can hide captured lazy resources.
    s = re.sub(
        r'<noscript>\s*<style[^>]*id=["\']rocket-lazyload-nojs-css["\'][^>]*>.*?</style>\s*</noscript>',
        '',
        s,
        flags=re.I | re.S,
    )

    # Remove lazyload-only classes that can leave opacity/display state waiting for JS.
    s = re.sub(r'\b(?:lazyload|lazyloaded|entered|exited)\b', '', s)

    p.write_text(s)
    print(p.relative_to(ROOT), "changed", s != before)

# Verify the three page documents no longer rely on WP Rocket data-lazy-src.
issues = []
for p in PAGES:
    s = p.read_text(errors="ignore")
    for token in ["data-lazy-src=", "data-lazy-srcset=", "/wp-rocket/assets/js/lazyload/"]:
        if token in s:
            issues.append(f"{p.relative_to(ROOT)} still contains {token}")

report = ROOT / "RUNTIME_ASSET_FIX.txt"
report.write_text(
    "RUNTIME ASSET FIX\n\n"
    "WP Rocket lazy loading removed from the three target pages.\n"
    "Captured local image, iframe, video and responsive image URLs are now assigned directly to browser src/srcset attributes.\n"
    "This prevents placeholder SVGs from remaining visible when the captured lazy loader fails to initialise.\n"
    f"Verification issues: {len(issues)}\n"
    + ("\n".join(issues) if issues else "No lazy-loader dependency remains on the target pages.\n")
)

if issues:
    raise SystemExit("\n".join(issues))
