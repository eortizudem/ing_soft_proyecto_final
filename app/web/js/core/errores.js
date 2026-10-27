// PS-S3-06: reporta al servidor los errores de JavaScript no capturados (bitacora, accion 'error_sistema').
// Limite en el navegador: 5 por carga de página, sin repetir el mismo mensaje (el servidor también limita).
import { api } from '/js/core/api.js';

const MAX = 5;
const seen = new Set();

function report(message, source) {
  const text = String(message || '').slice(0, 120);
  if (!text || seen.has(text) || seen.size >= MAX) return;
  seen.add(text);
  api.post('/errores', { mensaje: text, ruta: location.hash.slice(0, 40) || '/', origen: String(source || '').slice(0, 30) })
    .catch(() => {}); // un fallo al reportar nunca debe provocar otro error
}

export function install() {
  window.addEventListener('error', (e) => report(e.message, e.filename ? `${e.filename.split('/').pop()}:${e.lineno}` : 'error'));
  window.addEventListener('unhandledrejection', (e) => report(e.reason?.message || e.reason, 'promesa'));
}
