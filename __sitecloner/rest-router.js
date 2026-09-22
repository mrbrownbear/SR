(() => {
  const mapRest = (u) => {
    try {
      const a = new URL(String(u && u.url ? u.url : u), location.href);
      const m = a.pathname.match(/(?:blocked|wp-json\/)?sliderrevolution\/sliders\/(\d+)/);
      if (!m) return u;
      const mid = m[1];
      const sid = a.searchParams.get('slideid') || '';
      return sid
        ? `/__sitecloner/rest/${mid}-${sid}.json`
        : `/__sitecloner/rest/${mid}.json`;
    } catch (e) {
      return u;
    }
  };

  const oldFetch = window.fetch && window.fetch.bind(window);
  if (oldFetch) {
    window.fetch = (u, o) => oldFetch(mapRest(u), o);
  }

  const oldOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    return oldOpen.call(this, method, mapRest(url), ...rest);
  };

  const trimTemplateChrome = () => {
    document.querySelectorAll('header, footer').forEach((el) => el.remove());

    const content = document.querySelector('.entry-content');
    const marker = document.getElementById('h-what-makes-this-slider-revolution-template-a-must-have');
    if (!content || !marker || !content.contains(marker)) return;

    let cut = marker;
    while (cut.parentElement && cut.parentElement !== content) {
      cut = cut.parentElement;
    }

    if (cut.parentElement !== content) return;

    let node = cut;
    while (node) {
      const next = node.nextElementSibling;
      node.remove();
      node = next;
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', trimTemplateChrome, { once: true });
  } else {
    trimTemplateChrome();
  }
})();
