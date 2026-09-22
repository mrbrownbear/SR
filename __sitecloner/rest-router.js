(() => {
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
