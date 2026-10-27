// Prestamos API calls (no HTML, no DOM).
import { api, query, LIST_LIMIT } from '/js/core/api.js';

const id = (value) => encodeURIComponent(value);

export const list = ({ estado = '', q = '', matricula = '' } = {}) => api.get('/prestamos' + query({ estado, q, matricula, limite: LIST_LIMIT }));
export const get = (value) => api.get('/prestamos/' + id(value));
export const recibo = (value) => api.get(`/prestamos/${id(value)}/recibo`);
export const renovar = (value) => api.post(`/prestamos/${id(value)}/renovar`);
export const devolver = (value) => api.post(`/prestamos/${id(value)}/devolver`);
export const enviarRecibo = (value, canales) => api.post(`/prestamos/${id(value)}/recibo/enviar`, { canales });

export const validar = ({ matricula, clave }) => api.post('/prestamos/validar', { matricula: matricula.trim(), clave: clave.trim() });

// Form values (checkboxes canal_email / canal_whatsapp) -> API payload.
export const crear = (data) => api.post('/prestamos', {
  matricula: data.matricula.trim(),
  clave: data.clave.trim(),
  canales: [data.canal_email && 'email', data.canal_whatsapp && 'whatsapp'].filter(Boolean),
});

export const politicas = () => api.get('/politicas');
export const politica = async (value) => (await politicas()).find((p) => String(p.id_politica) === String(value));
export const savePolitica = (value, data) => api.put('/politicas/' + id(value), {
  dias_prestamo: Number(data.dias_prestamo),
  max_libros: Number(data.max_libros),
  max_renovaciones: Number(data.max_renovaciones),
  multa_diaria: Number(data.multa_diaria),
});
