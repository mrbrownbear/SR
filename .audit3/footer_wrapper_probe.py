from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json,time

u="https://www.sliderrevolution.com/templates/filmstrip-hero-3d-image-carousel-collection/"
o=Options();o.add_argument("--headless=new");o.add_argument("--no-sandbox");o.add_argument("--disable-dev-shm-usage");o.add_argument("--window-size=1440,1200")
d=webdriver.Chrome(options=o);d.set_page_load_timeout(30)
try:
 d.get(u);time.sleep(3)
 data=d.execute_script("""
 const describe=e=>{if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return{
  tag:e.tagName,id:e.id,cls:String(e.className||'').slice(0,350),
  h:r.height,w:r.width,top:r.top+scrollY,
  position:s.position,display:s.display,overflow:s.overflow,transform:s.transform,
  marginTop:s.marginTop,marginBottom:s.marginBottom,paddingTop:s.paddingTop,paddingBottom:s.paddingBottom,
  zIndex:s.zIndex
 }};
 const fb=document.querySelector('#footerbg'),ft=document.querySelector('footer'),mh=document.querySelector('#masthead');
 const chain=[];let x=fb;while(x&&chain.length<8){chain.push(describe(x));x=x.parentElement}
 const fchain=[];x=ft;while(x&&fchain.length<8){fchain.push(describe(x));x=x.parentElement}
 const site=document.querySelector('.wp-site-blocks');
 const children=site?[...site.children].map(describe):[];
 const top=[...document.querySelectorAll('header,nav,[id*="menu"],[class*="menu"]')].map(describe).filter(x=>x&&x.h>20).slice(0,60);
 return {bodyH:document.body.scrollHeight,footerbg:describe(fb),footer:describe(ft),footerChain:chain,footerTagChain:fchain,siteChildren:children,top};
 """)
 print(json.dumps(data,indent=2))
finally:d.quit()
