// Guarda el juego en el teléfono: abre al instante desde la copia guardada y en segundo plano revisa si hay versión nueva.
// Las cuentas y el chat siempre van por internet (otro origen, no pasan por aquí).
var CACHE = 'calabozo-v9';
var FILES = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './modelos/moto-azul.glb', './modelos/moto-azul-lejos.glb'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return Promise.all(FILES.map(function (f) { return c.add(f).catch(function () {}); })); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); }));
});
function avisar() { self.clients.matchAll().then(function (cs) { cs.forEach(function (c) { c.postMessage({ t: 'nueva' }); }); }); }
self.addEventListener('fetch', function (e) {
  var r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin) return;
  e.respondWith(caches.match(r, { ignoreSearch: true }).then(function (hit) {
    var red = fetch(r).then(function (res) {
      if (res && res.ok) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) {
          if (hit && (r.mode === 'navigate' || /index\.html$/.test(u.pathname))) { var a = hit.headers.get('etag') || hit.headers.get('last-modified'), b = res.headers.get('etag') || res.headers.get('last-modified'); if (a && b && a !== b) avisar(); }
          c.put(r, copy);
        });
      }
      return res;
    });
    // con copia guardada: se abre al instante y se actualiza detrás; sin copia: se baja de internet
    return hit ? (red.catch(function () {}), hit) : red.catch(function () { return caches.match('./index.html'); });
  }));
});
