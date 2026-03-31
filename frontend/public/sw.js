const CACHE_NAME = 'agendahub-v1';
const STATIC_CACHE = 'agendahub-static-v1';
const DYNAMIC_CACHE = 'agendahub-dynamic-v1';

// Arquivos para cache estático
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json'
];

// URLs de API que devem usar network-first
const API_PATTERNS = [
  '/api/'
];

// Instalar service worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Ativar service worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== DYNAMIC_CACHE)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// Estratégia: Network First para API, Cache First para assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorar requests não-GET
  if (request.method !== 'GET') return;

  // Ignorar extensões do Chrome e outros protocolos
  if (!url.protocol.startsWith('http')) return;

  // Verificar se é uma chamada de API
  const isApiCall = API_PATTERNS.some(pattern => url.pathname.includes(pattern));

  if (isApiCall) {
    // Network First para API
    event.respondWith(networkFirst(request));
  } else {
    // Cache First para assets estáticos
    event.respondWith(cacheFirst(request));
  }
});

// Estratégia Network First
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Cachear resposta se for válida
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    // Fallback para cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Retornar resposta de erro offline
    return new Response(
      JSON.stringify({ error: 'Offline', message: 'Você está offline. Verifique sua conexão.' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// Estratégia Cache First
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    // Atualizar cache em background
    fetch(request).then((response) => {
      if (response.ok) {
        caches.open(DYNAMIC_CACHE).then((cache) => {
          cache.put(request, response);
        });
      }
    }).catch(() => {});
    
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    // Retornar página offline para navegação
    if (request.mode === 'navigate') {
      return caches.match('/');
    }
    throw error;
  }
}

// Escutar mensagens do app
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});
