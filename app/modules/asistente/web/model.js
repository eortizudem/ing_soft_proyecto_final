/** @module modules/asistente/model — llamadas a la API del asistente (`/api/asistente/*`) y sugerencias rápidas. */
import { api, query } from '/js/core/api.js';

/**
 * Envía un mensaje al asistente (POST /api/asistente/mensajes).
 * @param {string} texto - mensaje del usuario (1-500 caracteres).
 * @param {number|null} [idConversacion] - conversación activa; vacío abre una nueva.
 * @param {string} [canal='web'] - `web` o `movil`.
 * @returns {Promise<{id_conversacion: number, respuesta: {texto: string, intencion: string, con_bibliotecario: boolean, libros?: Array<object>, enlaces?: Array<{texto: string, ruta: string}>}}>}
 */
export const send = (texto, idConversacion, canal = 'web') =>
  api.post('/asistente/mensajes', { texto, id_conversacion: idConversacion || undefined, canal });
/**
 * Obtiene una conversación con sus mensajes (GET /api/asistente/conversaciones/:id).
 * @param {number|string} id - id de la conversación.
 * @returns {Promise<{id_conversacion: number, resuelta: boolean, calificacion: number|null, mensajes: Array<{emisor: string, texto: string, fecha: string}>, usuario?: object|null}>}
 */
export const get = (id) => api.get('/asistente/conversaciones/' + encodeURIComponent(id));
/**
 * Califica la conversación (POST /api/asistente/conversaciones/:id/opinion).
 * @param {number|string} id - id de la conversación.
 * @param {number|string} calificacion - 1 a 5.
 * @param {boolean} [resuelta] - si la duda quedó resuelta.
 * @returns {Promise<object>} conversación actualizada.
 */
export const rate = (id, calificacion, resuelta) =>
  api.post(`/asistente/conversaciones/${encodeURIComponent(id)}/opinion`, { calificacion: Number(calificacion), resuelta });
/**
 * Lista las consultas escaladas al bibliotecario (GET /api/asistente/consultas?estado=).
 * @param {{estado?: string}} [filtros] - `''` (todas), `pendiente` o `resuelta`.
 * @returns {Promise<Array<{id_conversacion: number, fecha_inicio: string, resuelta: boolean, ultimo_mensaje: string, usuario: object|null}>>}
 */
export const consultas = ({ estado = '' } = {}) => api.get('/asistente/consultas' + query({ estado }));
/**
 * Responde y cierra una consulta (POST /api/asistente/consultas/:id/resolver).
 * @param {number|string} id - id de la conversación.
 * @param {string} respuesta - texto para el usuario (se recorta con trim; máx. 500).
 * @returns {Promise<object>} conversación resuelta.
 */
export const resolve = (id, respuesta) =>
  api.post(`/asistente/consultas/${encodeURIComponent(id)}/resolver`, { respuesta: respuesta.trim() });

/**
 * Chips de sugerencias (respuestas rápidas) mostrados sobre el chat.
 * @type {string[]}
 */
export const SUGGESTIONS = [
  '¿Cuál es el horario de la biblioteca?', '¿Cuántos libros puedo llevar?', '¿Cómo renuevo un préstamo?',
  '¿Cuánto cuesta un retraso?', 'Busco un libro', 'Mis préstamos', 'Hablar con un bibliotecario',
];
