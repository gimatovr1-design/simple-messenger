self.addEventListener("install", () => {
    self.skipWaiting();
});

self.addEventListener("activate", () => {
    clients.claim();
});

self.addEventListener("push", event => {
    const data = event.data.json();
    self.registration.showNotification(data.title, {
        body: data.body,
        icon: "/icon-192.png"
    });
});
