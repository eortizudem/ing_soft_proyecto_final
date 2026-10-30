/**
 * @module core/errores — PS-S3-06: reporta al servidor los errores de JavaScript no capturados (bitácora, acción 'error_sistema').
 * Límite en el navegador: 5 por carga de página, sin repetir el mismo mensaje (el servidor también limita).
 */
import { api } from '/js/core/api.js';

/** @type {number} Máximo de reportes distintos por carga de página. */
const MAX = 5;
/** @type {Set<string>} Mensajes ya reportados. */
const seen = new Set();

/**
 * Envía un error a `/errores` si es nuevo y no se superó el límite; nunca lanza.
 * @param {any} message - Mensaje del error (se recorta a 120 caracteres).
 * @param {string} source - Origen (archivo:línea, 'promesa' o 'error'; se recorta a 30).
 */
function report(message, source) {
  const text = String(message || '').slice(0, 120);
  if (!text || seen.has(text) || seen.size >= MAX) return;
  seen.add(text);
  api.post('/errores', { mensaje: text, ruta: location.hash.slice(0, 40) || '/', origen: String(source || '').slice(0, 30) })
    .catch(() => {}); // un fallo al reportar nunca debe provocar otro error
}

/**
 * Instala los listeners globales `error` y `unhandledrejection`.
 * @returns {void}
 */
export function install() {
  window.addEventListener('error', (e) => report(e.message, e.filename ? `${e.filename.split('/').pop()}:${e.lineno}` : 'error'));
  window.addEventListener('unhandledrejection', (e) => report(e.reason?.message || e.reason, 'promesa'));
}
