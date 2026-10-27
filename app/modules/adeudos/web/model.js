// Adeudos API calls.
import { api, query, LIST_LIMIT } from '/js/core/api.js';

const id = encodeURIComponent;

export const list = ({ q = '', estado = '', tipo = '' } = {}) => api.get('/adeudos' + query({ q, estado, tipo, limite: LIST_LIMIT }));
export const get = (n) => api.get('/adeudos/' + id(n));
export const pay = (n, data) => api.post(`/adeudos/${id(n)}/pago`, {
  referencia_tesoreria: (data.referencia_tesoreria || '').trim(),
  fecha_pago: data.fecha_pago || undefined,
});
export const cancelFine = (n, motivo) => api.post(`/adeudos/${id(n)}/cancelar`, { motivo });
export const exchangeRate = () => api.get('/tipo-cambio');
// Loan data + computed amounts (replacement value, damage amount) for confirmation screens.
export const preview = (loan, { tipo_cambio = '', porcentaje = '' } = {}) =>
  api.get(`/adeudos/prestamo/${id(loan)}` + query({ tipo_cambio, porcentaje }));
export const reportLoss = (loan, { tipo_cambio, observacion }) => api.post('/adeudos/perdida', {
  id_prestamo: Number(loan),
  tipo_cambio: tipo_cambio ? Number(tipo_cambio) : undefined,
  observacion: (observacion || '').trim() || undefined,
});
export const reportDamage = (loan, { porcentaje, observacion, dar_baja }) => api.post('/adeudos/danio', {
  id_prestamo: Number(loan),
  porcentaje: Number(porcentaje) || undefined,
  observacion: (observacion || '').trim() || undefined,
  dar_baja: !!dar_baja,
});
