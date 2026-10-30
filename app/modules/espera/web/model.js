/**
 * @module modules/espera/model — llamadas a la API de la lista de espera (capa model).
 */
import { api, query } from '/js/core/api.js';

/**
 * GET /api/espera — lista la espera (personal, permiso `espera`).
 * @param {Object} [filters] - Filtros.
 * @param {string} [filters.q] - Búsqueda libre.
 * @param {string} [filters.estado] - Estado de la entrada.
 * @param {string|number} [filters.id_libro] - Libro.
 * @returns {Promise<Array<Object>>} Entradas con `usuario` y `libro` anidados.
 */
export const list = ({ q = '', estado = '', id_libro = '' } = {}) => api.get('/espera' + query({ q, estado, id_libro }));
/**
 * GET /api/espera/mias — solicitudes del usuario autenticado.
 * @returns {Promise<Array<Object>>} Entradas propias.
 */
export const mine = () => api.get('/espera/mias');
/**
 * GET /api/espera/libros — libros candidatos a espera con disponibilidad.
 * @returns {Promise<Array<Object>>} Libros con `id_libro`, `clave`, `titulo`, `disponibles`, `en_espera`.
 */
export const libros = () => api.get('/espera/libros');
/**
 * GET /api/libros/:id — datos de un libro (endpoint del módulo de libros).
 * @param {string|number} id - Id del libro.
 * @returns {Promise<Object>} Libro.
 */
export const libro = (id) => api.get('/libros/' + encodeURIComponent(id));
/**
 * POST /api/espera — alta por el personal.
 * @param {Object} data - Valores del formulario.
 * @param {string} data.matricula - Matrícula o nómina.
 * @param {string|number} data.id_libro - Libro esperado.
 * @returns {Promise<Object>} Entrada creada.
 */
export const create = (data) => api.post('/espera', { matricula: data.matricula.trim(), id_libro: Number(data.id_libro) });
/**
 * POST /api/espera/unirse — el usuario autenticado se une a la espera de un libro.
 * @param {string|number} idLibro - Id del libro.
 * @returns {Promise<Object>} Entrada creada.
 */
export const join = (idLibro) => api.post('/espera/unirse', { id_libro: Number(idLibro) });
/**
 * DELETE /api/espera/:id — cancela una entrada.
 * @param {string|number} id - Id de la entrada de espera.
 * @returns {Promise<Object>} Entrada cancelada.
 */
export const cancel = (id) => api.delete(`/espera/${encodeURIComponent(id)}`);
