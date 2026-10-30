/** @module modules/perfiles/model — llamadas a la API `/api/roles` para la matriz de permisos */
import { api } from '/js/core/api.js';

/**
 * Matriz de perfiles y permisos. Llama a GET /api/roles (requiere sesión).
 * @returns {Promise<{roles: Object[], permisos: Object[], matriz: Object<string, Object<string, boolean>>}>}
 */
export const matrix = () => api.get('/roles');
/**
 * Habilita o deshabilita un permiso de un perfil. Llama a PUT /api/roles/:rol/permisos/:permiso (permiso `perfiles`).
 * @param {string} rol - Nombre del perfil.
 * @param {string} permiso - Nombre del permiso.
 * @param {boolean} habilitado - Nuevo valor.
 * @returns {Promise<{roles: Object[], permisos: Object[], matriz: Object}>} Matriz actualizada.
 */
export const setPermission = (rol, permiso, habilitado) =>
  api.put(`/roles/${encodeURIComponent(rol)}/permisos/${encodeURIComponent(permiso)}`, { habilitado });
