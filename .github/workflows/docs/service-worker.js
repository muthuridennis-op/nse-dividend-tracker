const CACHE = "nse-shell-v1";
const ASSETS = ["./", "./index.html", "./manifest.json", "./config.js", "./icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // Never cache the Streamlit app itself — always fetch live
  if (e.request.url.includes("streamlit.app")) return;
  e.respondWith(
    caches.match(e.request).then((r) => r || fetch(e.request))
  );
});