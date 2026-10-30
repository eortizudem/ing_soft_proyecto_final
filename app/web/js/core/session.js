/** @module core/session — usuario actual y comprobaciones de permisos. */
import { api } from './api.js';

/** @type {?Object} Usuario autenticado (`permisos`, `rol`, ...) o null. */
let user = null;

/** Devuelve el usuario actual. @returns {?Object} */
export const get = () => user;
/** Establece el usuario actual. @param {?Object} value - Usuario. @returns {void} */
export const set = (value) => { user = value; };
/** Elimina el usuario actual. @returns {void} */
export const clear = () => { user = null; };
/**
 * Indica si el usuario tiene un permiso.
 * @param {string} permission - Clave de permiso.
 * @returns {boolean}
 */
export const can = (permission) => !!user && user.permisos.includes(permission);
/**
 * Indica si el usuario tiene al menos uno de los permisos.
 * @param {string[]} list - Claves de permiso.
 * @returns {boolean}
 */
export const canAny = (list) => list.some(can);
/** Indica si la sesión es de visitante. @returns {boolean} */
export const isVisitor = () => user?.rol === 'visitante';

/**
 * Recarga el usuario desde el servidor (también tras cambios de permisos).
 * @returns {Promise<?Object>} El usuario, o null si no hay sesión.
 */
export async function load() {
  try {
    user = (await api.get('/me')).user;
  } catch {
    user = null;
  }
  return user;
}
