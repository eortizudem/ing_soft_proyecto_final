// Notifications API calls.
import { api, query } from '/js/core/api.js';

// periodo = number of days back ('' = all); the API filters by `desde` (ISO date, local).
function since(periodo) {
  if (!periodo) return '';
  const d = new Date();
  d.setDate(d.getDate() - (Number(periodo) - 1));
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const fetchWith = (path) => ({ canal = '', q = '', periodo = '' } = {}) =>
  api.get(path + query({ canal, q, desde: since(periodo) }));

export const list = fetchWith('/notificaciones');
export const mine = fetchWith('/notificaciones/mias');
