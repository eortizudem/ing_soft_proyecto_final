/** @module modules/notificaciones/model — llamadas a la API de notificaciones simuladas (`/api/notificaciones*`). */
import { api, query } from '/js/core/api.js';

/**
 * Convierte un periodo en días hacia atrás en la fecha ISO local `desde` que espera la API.
 * @param {string|number} periodo - número de días (`1` = hoy); vacío = todo el historial.
 * @returns {string} fecha `AAAA-MM-DD` o cadena vacía.
 */
function since(periodo) {
  if (!periodo) return '';
  const d = new Date();
  d.setDate(d.getDate() - (Number(periodo) - 1));
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * Crea una función de consulta con filtros para una ruta de notificaciones.
 * @param {string} path - ruta de la API.
 * @returns {function({canal?: string, q?: string, periodo?: string}=): Promise<Array<object>>} consulta (GET path?canal&q&desde).
 */
const fetchWith = (path) => ({ canal = '', q = '', periodo = '' } = {}) =>
  api.get(path + query({ canal, q, desde: since(periodo) }));

/**
 * Lista de avisos de todos los usuarios, permiso `notificaciones` (GET /api/notificaciones).
 * @type {function({canal?: string, q?: string, periodo?: string}=): Promise<Array<{id_bitacora: number, canal: string, destino: string, asunto: string, cuerpo: string, fecha: string, usuario: object}>>}
 */
export const list = fetchWith('/notificaciones');
/**
 * Avisos del usuario actual (GET /api/notificaciones/mias).
 * @type {function({canal?: string, q?: string, periodo?: string}=): Promise<Array<object>>}
 */
export const mine = fetchWith('/notificaciones/mias');
