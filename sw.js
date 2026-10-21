// Abre rápido y siempre trae la versión más nueva: pregunta al servidor si cambió (si no cambió responde 304 y es instantáneo)
// y, si la red tarda más de 3 s o no hay internet, abre la copia guardada. Cuentas y chat van por internet (otro origen).
var CACHE = 'calabozo-v10';
var FILES = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './modelos/moto-azul.glb', './modelos/moto-azul-lejos.glb'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return Promise.all(FILES.map(function (f) { return c.add(new Request(f, { cache: 'reload' })).catch(function () {}); })); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); }));
});
function avisar() { self.clients.matchAll().then(function (cs) { cs.forEach(function (c) { c.postMessage({ t: 'nueva' }); }); }); }
self.addEventListener('fetch', function (e) {
  var r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin) return;
  var esPagina = r.mode === 'navigate' || /(^|\/)(index\.html)?$/.test(u.pathname);
  e.respondWith(caches.match(r, { ignoreSearch: true }).then(function (hit) {
    var red = fetch(r, { cache: 'no-cache' }).then(function (res) {
      if (res && res.ok) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) {
          if (hit && esPagina) { var a = hit.headers.get('etag') || hit.headers.get('last-modified'), b = res.headers.get('etag') || res.headers.get('last-modified'); if (a && b && a !== b && e.__tarde) avisar(); }
          c.put(r, copy);
        });
      }
      return res;
    });
    if (!hit) return red.catch(function () { return caches.match('./index.html'); });
    // con copia guardada: gana la red si responde en 3 s; si no, se abre la copia y la red sigue actualizando detrás
    return new Promise(function (ok) {
      var listo = false;
      var t = setTimeout(function () { if (!listo) { listo = true; e.__tarde = true; ok(hit); } }, 3000);
      red.then(function (res) { if (!listo) { listo = true; clearTimeout(t); ok(res); } }, function () { if (!listo) { listo = true; clearTimeout(t); ok(hit); } });
    });
  }));
});
