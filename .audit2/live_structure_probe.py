from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json,time

urls=[
"https://www.sliderrevolution.com/templates/carousel-design-templates-wordpress-pack/",
"https://www.sliderrevolution.com/templates/korr-artistic-horizontal-portfolio-carousel/",
"https://www.sliderrevolution.com/templates/filmstrip-hero-3d-image-carousel-collection/",
]
o=Options();o.add_argument("--headless=new");o.add_argument("--no-sandbox");o.add_argument("--disable-dev-shm-usage");o.add_argument("--window-size=1440,1200")
d=webdriver.Chrome(options=o);d.set_page_load_timeout(30)
try:
 for u in urls:
  print("\n===",u,"===")
  d.get(u);time.sleep(3)
  data=d.execute_script("""
    const arr=[...document.body.children].map((e,i)=>{
      const r=e.getBoundingClientRect(),s=getComputedStyle(e);
      return {i,tag:e.tagName,id:e.id,cls:e.className&&String(e.className).slice(0,300),
        h:r.height,top:r.top+scrollY,disp:s.display,txt:(e.innerText||'').trim().slice(0,180)};
    });
    const all=[...document.querySelectorAll('*')].map((e)=>{
      const r=e.getBoundingClientRect(),s=getComputedStyle(e),c=String(e.className||'');
      return {tag:e.tagName,id:e.id,cls:c.slice(0,220),h:r.height,top:r.top+scrollY,disp:s.display,
        txt:(e.innerText||'').trim().slice(0,100)};
    }).filter(x=>x.h>40 && /(footer|menu|nav|header|masthead|copyright|bottom|mega)/i.test(x.id+' '+x.cls));
    return {children:arr,interesting:all.slice(0,120),bodyH:document.body.scrollHeight};
  """)
  print(json.dumps(data,indent=2))
finally:d.quit()
