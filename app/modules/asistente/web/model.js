// Asistente API calls.
import { api, query } from '/js/core/api.js';

export const send = (texto, idConversacion, canal = 'web') =>
  api.post('/asistente/mensajes', { texto, id_conversacion: idConversacion || undefined, canal });
export const get = (id) => api.get('/asistente/conversaciones/' + encodeURIComponent(id));
export const rate = (id, calificacion, resuelta) =>
  api.post(`/asistente/conversaciones/${encodeURIComponent(id)}/opinion`, { calificacion: Number(calificacion), resuelta });
export const consultas = ({ estado = '' } = {}) => api.get('/asistente/consultas' + query({ estado }));
export const resolve = (id, respuesta) =>
  api.post(`/asistente/consultas/${encodeURIComponent(id)}/resolver`, { respuesta: respuesta.trim() });

/** Suggestion chips (quick replies). */
export const SUGGESTIONS = [
  '¿Cuál es el horario de la biblioteca?', '¿Cuántos libros puedo llevar?', '¿Cómo renuevo un préstamo?',
  '¿Cuánto cuesta un retraso?', 'Busco un libro', 'Mis préstamos', 'Hablar con un bibliotecario',
];
