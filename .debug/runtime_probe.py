from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from pathlib import Path
import json, time, os, sys

BASE="http://127.0.0.1:8000"
ROUTES=[
    ("/","root"),
    ("/korr-artistic-horizontal-portfolio-carousel/","korr"),
    ("/filmstrip-hero-3d-image-carousel-collection/","filmstrip"),
]
out=Path("runtime-probe")
out.mkdir(exist_ok=True)

opts=Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1440,1200")
opts.set_capability("goog:loggingPrefs", {"browser":"ALL","performance":"ALL"})

driver=webdriver.Chrome(options=opts)
failed_total=0
try:
    for route,name in ROUTES:
        print("\n===== ROUTE",route,"=====")
        driver.get(BASE+route)
        time.sleep(6)
        driver.execute_script("window.scrollTo(0, Math.min(document.body.scrollHeight, 1800));")
        time.sleep(2)
        state=driver.execute_script("""
          const mods = window.SR7 && SR7.M ? Object.fromEntries(Object.entries(SR7.M).map(([k,v])=>[k,{
            states:v.states||null,
            settings:!!v.settings,
            module:!!(v.c&&v.c.module),
            slides:v.c&&v.c.module ? v.c.module.querySelectorAll('sr7-slide').length : null
          }])) : null;
          const imgs=[...document.images];
          const badImgs=imgs.filter(i=>!i.complete || i.naturalWidth===0).map(i=>({src:i.currentSrc||i.src, cls:i.className})).slice(0,50);
          const modules=[...document.querySelectorAll('sr7-module')].map(m=>({
            id:m.id,
            rect:m.getBoundingClientRect().toJSON(),
            display:getComputedStyle(m).display,
            visibility:getComputedStyle(m).visibility,
            opacity:getComputedStyle(m).opacity
          }));
          return {
            ready:document.readyState,
            title:document.title,
            bodyHeight:document.body.scrollHeight,
            sr7Exists:!!window.SR7,
            sr7Keys:window.SR7?Object.keys(SR7):[],
            modules,
            sr7Modules:mods,
            images:{total:imgs.length,bad:badImgs},
            scripts:[...document.scripts].map(s=>s.src).filter(Boolean),
            styles:[...document.querySelectorAll('link[rel="stylesheet"]')].map(l=>l.href),
            webgl:(()=>{try{const c=document.createElement('canvas');return !!(c.getContext('webgl2')||c.getContext('webgl'))}catch(e){return String(e)}})()
          }
        """)
        print("STATE",json.dumps(state,default=str))
        logs=driver.get_log("browser")
        for item in logs:
            print("BROWSER",json.dumps(item))
        perf=driver.get_log("performance")
        failed=[]
        responses=[]
        for item in perf:
            try:
                msg=json.loads(item["message"])["message"]
            except Exception:
                continue
            if msg["method"]=="Network.loadingFailed":
                p=msg["params"]; failed.append({"error":p.get("errorText"),"type":p.get("type"),"blocked":p.get("blockedReason")})
            elif msg["method"]=="Network.responseReceived":
                p=msg["params"]; r=p["response"]
                if r.get("status",0)>=400:
                    responses.append({"status":r.get("status"),"url":r.get("url"),"mime":r.get("mimeType")})
        print("NETWORK_FAILED",json.dumps(failed[:100]))
        print("HTTP_ERRORS",json.dumps(responses[:100]))
        failed_total += len(failed)+len(responses)
        driver.save_screenshot(str(out/f"{name}.png"))
finally:
    driver.quit()
print("\nFAILED_TOTAL",failed_total)
