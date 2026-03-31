// socket.js
// Centraliza a montagem da URL do WebSocket para o AgendaOps

const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export function buildWebSocketUrl() {
  try {
    const url = new URL(backendUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/ws`;
  } catch (error) {
    console.error('[socket] Erro ao montar URL do WebSocket:', error);
    return 'ws://localhost:8000/ws';
  }
}

export function createWebSocket() {
  const wsUrl = buildWebSocketUrl();
  return new WebSocket(wsUrl);
}
