from __future__ import annotations
from pathlib import Path
import base64, gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.bootstrap' / 'asset-manifest.tsv'
MANIFEST_B64 = '''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'''
MANIFEST.write_bytes(gzip.decompress(base64.b64decode(MANIFEST_B64)))
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36'
REFERER = 'https://www.sliderrevolution.com/'
PAGES = {
    'https://www.sliderrevolution.com/templates/carousel-design-templates-wordpress-pack/': 'index.html',
    'https://www.sliderrevolution.com/templates/korr-artistic-horizontal-portfolio-carousel/': 'korr-artistic-horizontal-portfolio-carousel/index.html',
    'https://www.sliderrevolution.com/templates/filmstrip-hero-3d-image-carousel-collection/': 'filmstrip-hero-3d-image-carousel-collection/index.html',
}

def curl_fetch(url: str, rel: str) -> tuple[str, bool, str]:
    dest = ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + '.part')
    cmd = [
        'curl', '-fL', '--compressed', '--retry', '4', '--retry-delay', '2',
        '--retry-all-errors', '--connect-timeout', '25', '--max-time', '180',
        '-A', UA, '-e', REFERER,
        '-H', 'Accept: */*', '-H', 'Cache-Control: no-cache',
        '-o', str(tmp), url,
    ]
    last = ''
    for attempt in range(3):
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            tmp.replace(dest)
            return rel, True, ''
        last = (proc.stderr or proc.stdout)[-1500:]
        time.sleep(2 + attempt * 2)
    try: tmp.unlink(missing_ok=True)
    except Exception: pass
    return rel, False, f'{url}\\n{last}'

entries = []
for line in MANIFEST.read_text().splitlines():
    if not line.strip():
        continue
    url, rel = line.split('	', 1)
    entries.append((url, rel))

# Pages first so a Cloudflare or connectivity problem is immediately obvious.
for url, rel in PAGES.items():
    name, ok, err = curl_fetch(url, rel)
    print(('OK   ' if ok else 'FAIL ') + name)
    if not ok:
        print(err, file=sys.stderr)
        raise SystemExit(1)

failures = []
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(curl_fetch, u, r) for u, r in entries]
    done = 0
    for fut in as_completed(futs):
        rel, ok, err = fut.result()
        done += 1
        if not ok:
            failures.append((rel, err))
            print('FAIL', rel)
        elif done % 25 == 0:
            print(f'Fetched {done}/{len(entries)} assets')

if failures:
    print(f'\\n{len(failures)} asset downloads failed:', file=sys.stderr)
    for rel, err in failures:
        print(f'\\n[{rel}]\\n{err}', file=sys.stderr)
    raise SystemExit(2)
print(f'Fetched all {len(entries)} assets')
