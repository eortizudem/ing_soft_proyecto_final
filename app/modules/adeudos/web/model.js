/**
 * @module modules/adeudos/model — llamadas a la API de adeudos, pérdida, daño y tipo de cambio (capa model).
 */
import { api, query, LIST_LIMIT } from '/js/core/api.js';

/**
 * Codifica un valor para usarlo como segmento de URL.
 * @type {function(string|number): string}
 */
const id = encodeURIComponent;

/**
 * GET /api/adeudos — lista adeudos con filtros (tope `LIST_LIMIT`).
 * @param {Object} [filters] - Filtros.
 * @param {string} [filters.q] - Búsqueda libre.
 * @param {string} [filters.estado] - 'pendiente', 'pagado' o 'cancelado'.
 * @param {string} [filters.tipo] - 'retraso', 'danio' o 'perdida'.
 * @returns {Promise<Array<Object>>} Adeudos con `usuario` y `libro`.
 */
export const list = ({ q = '', estado = '', tipo = '' } = {}) => api.get('/adeudos' + query({ q, estado, tipo, limite: LIST_LIMIT }));
/**
 * GET /api/adeudos/:id — detalle con referencia de Tesorería y motivo de cancelación.
 * @param {string|number} n - Id del adeudo.
 * @returns {Promise<Object>} Adeudo.
 */
export const get = (n) => api.get('/adeudos/' + id(n));
/**
 * POST /api/adeudos/:id/pago — registra el pago (D-10).
 * @param {string|number} n - Id del adeudo.
 * @param {Object} data - Valores del formulario.
 * @param {string} data.referencia_tesoreria - Referencia del comprobante de Tesorería.
 * @param {string} [data.fecha_pago] - Fecha ISO; si falta, el servidor usa hoy.
 * @returns {Promise<Object>} Adeudo pagado.
 */
export const pay = (n, data) => api.post(`/adeudos/${id(n)}/pago`, {
  referencia_tesoreria: (data.referencia_tesoreria || '').trim(),
  fecha_pago: data.fecha_pago || undefined,
});
/**
 * POST /api/adeudos/:id/cancelar — cancela el adeudo (solo admin, D-04).
 * @param {string|number} n - Id del adeudo.
 * @param {string} motivo - Motivo de la cancelación.
 * @returns {Promise<Object>} Adeudo cancelado.
 */
export const cancelFine = (n, motivo) => api.post(`/adeudos/${id(n)}/cancelar`, { motivo });
/**
 * GET /api/tipo-cambio — tipo de cambio USD/MXN simulado.
 * @returns {Promise<Object>} `{ usd_mxn, fuente, nota }`.
 */
export const exchangeRate = () => api.get('/tipo-cambio');
// Loan data + computed amounts (replacement value, damage amount) for confirmation screens.
/**
 * GET /api/adeudos/prestamo/:id — datos del préstamo y montos calculados (reposición, daño) sin escribir.
 * @param {string|number} loan - Id del préstamo.
 * @param {Object} [opts] - Parámetros opcionales.
 * @param {string|number} [opts.tipo_cambio] - Tipo de cambio alternativo.
 * @param {string|number} [opts.porcentaje] - Porcentaje de daño (10-100).
 * @returns {Promise<Object>} Previsualización con `reposicion`, `monto_danio`, `monto_retraso`.
 */
export const preview = (loan, { tipo_cambio = '', porcentaje = '' } = {}) =>
  api.get(`/adeudos/prestamo/${id(loan)}` + query({ tipo_cambio, porcentaje }));
/**
 * POST /api/adeudos/perdida — registra la pérdida del ejemplar (RN-04).
 * @param {string|number} loan - Id del préstamo.
 * @param {Object} data - Valores del formulario.
 * @param {string|number} [data.tipo_cambio] - Tipo de cambio alternativo.
 * @param {string} [data.observacion] - Observación (máx. 100 caracteres).
 * @returns {Promise<Object>} Adeudos generados y monto de reposición.
 */
export const reportLoss = (loan, { tipo_cambio, observacion }) => api.post('/adeudos/perdida', {
  id_prestamo: Number(loan),
  tipo_cambio: tipo_cambio ? Number(tipo_cambio) : undefined,
  observacion: (observacion || '').trim() || undefined,
});
/**
 * POST /api/adeudos/danio — registra el daño del ejemplar (D-08).
 * @param {string|number} loan - Id del préstamo.
 * @param {Object} data - Valores del formulario.
 * @param {string|number} [data.porcentaje] - Porcentaje de la reposición (10-100; por omisión 50).
 * @param {string} [data.observacion] - Observación.
 * @param {boolean} [data.dar_baja] - Dar de baja el ejemplar.
 * @returns {Promise<Object>} Adeudo, devolución y espera notificada.
 */
export const reportDamage = (loan, { porcentaje, observacion, dar_baja }) => api.post('/adeudos/danio', {
  id_prestamo: Number(loan),
  porcentaje: Number(porcentaje) || undefined,
  observacion: (observacion || '').trim() || undefined,
  dar_baja: !!dar_baja,
});
