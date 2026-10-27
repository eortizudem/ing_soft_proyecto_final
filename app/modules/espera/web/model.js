// Waitlist API calls.
import { api, query } from '/js/core/api.js';

export const list = ({ q = '', estado = '', id_libro = '' } = {}) => api.get('/espera' + query({ q, estado, id_libro }));
export const mine = () => api.get('/espera/mias');
export const libros = () => api.get('/espera/libros');
export const libro = (id) => api.get('/libros/' + encodeURIComponent(id));
export const create = (data) => api.post('/espera', { matricula: data.matricula.trim(), id_libro: Number(data.id_libro) });
export const join = (idLibro) => api.post('/espera/unirse', { id_libro: Number(idLibro) });
export const cancel = (id) => api.delete(`/espera/${encodeURIComponent(id)}`);
