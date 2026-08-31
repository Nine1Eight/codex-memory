const CACHE="ai-launcher-v3";
const ASSETS=["./","./index.html","./style.css","./app.js","./manifest.json"];

self.addEventListener("install",e=>{
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)));
});

self.addEventListener("activate",e=>{
  e.waitUntil(
    caches.keys().then(keys=>
      Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))
    )
  );
});

self.addEventListener("fetch",e=>{
  e.respondWith(
    caches.match(e.request).then(res=>res||fetch(e.request))
  );
});
