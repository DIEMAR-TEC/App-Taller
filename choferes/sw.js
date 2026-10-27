importScripts('/choferes/cola.js');
const CACHE='choferes-shell-v10';
const FILES=['/choferes/','/choferes/app.js','/choferes/cola.js','/choferes/style.css','/choferes/manifest.webmanifest','/choferes/icon.svg','/choferes/icon.png'];
// La versión nueva reemplaza a la anterior sin esperar a que se cierren las pestañas.
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys()
 .then(ks=>Promise.all(ks.filter(k=>k.startsWith('choferes-shell-')&&k!==CACHE).map(k=>caches.delete(k))))
 .then(()=>self.clients.claim())));
// Primero la red, para que una publicación nueva se vea al recargar; la copia guardada, sólo sin señal.
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url);
 if(u.origin===location.origin && e.request.method==='GET' && FILES.includes(u.pathname))
   e.respondWith(caches.open(CACHE).then(async c=>{
     try{const r=await fetch(e.request,{cache:'no-store'});if(r.ok)await c.put(u.pathname,r.clone());return r;}
     catch(err){const r=await c.match(u.pathname);if(r)return r;throw err;}
   }));
});
self.addEventListener('sync',e=>{if(e.tag==='reportes-chofer')e.waitUntil(Cola.sync());});
