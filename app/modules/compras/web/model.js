/** @module modules/compras/model — llamadas a la API de solicitudes de compra y ayudas de validación */
// Purchase requests: API calls and validation helpers.
import { api } from '/js/core/api.js';

/**
 * Lista solicitudes. Llama a GET /api/compras.
 * @returns {Promise<Object[]>} Solicitudes con detalles.
 */
export const list = () => api.get('/compras');
/**
 * Obtiene una solicitud. Llama a GET /api/compras/:id.
 * @param {number|string} id - Id de la solicitud.
 * @returns {Promise<Object>} Solicitud con detalles.
 */
export const get = (id) => api.get('/compras/' + encodeURIComponent(id));
/**
 * Consulta el presupuesto mensual. Llama a GET /api/compras/presupuesto.
 * @param {string} [month] - Mes AAAA-MM; vacío = mes actual.
 * @returns {Promise<{mes: string, presupuesto_usd: number, usado_usd: number, disponible_usd: number}>} Presupuesto.
 */
export const budget = (month = '') => api.get('/compras/presupuesto' + (month ? '?mes=' + encodeURIComponent(month) : ''));
/**
 * Cancela una solicitud. Llama a POST /api/compras/:id/cancelar.
 * @param {number|string} id - Id de la solicitud.
 * @returns {Promise<Object>} Solicitud cancelada.
 */
export const cancel = (id) => api.post(`/compras/${encodeURIComponent(id)}/cancelar`, {});
/**
 * Registra la recepción del pedido. Llama a POST /api/compras/:id/recibir.
 * @param {number|string} id - Id de la solicitud.
 * @param {Object} payload - {factura_folio, factura_total, fecha_recepcion?, lineas: [{id_detalle, cantidad_recibida}]}.
 * @returns {Promise<Object>} Solicitud con `pendientes_catalogar`.
 */
export const receive = (id, payload) => api.post(`/compras/${encodeURIComponent(id)}/recibir`, payload);
/**
 * Envía una solicitud pendiente. Llama a POST /api/compras/:id/enviar.
 * @param {number|string} id - Id de la solicitud.
 * @returns {Promise<Object>} Solicitud enviada.
 */
export const send = (id) => api.post(`/compras/${encodeURIComponent(id)}/enviar`);

/**
 * Títulos de libros activos para autocompletar. Llama a GET /api/libros?estado=activo; ante error devuelve lista vacía.
 * @returns {Promise<string[]>} Títulos.
 */
export async function bookTitles() {
  try {
    return (await api.get('/libros?estado=activo')).map((b) => b.titulo);
  } catch {
    return [];
  }
}

/**
 * Total estimado de las líneas.
 * @param {Array<{cantidad: number|string, precio_unitario: number|string}>} lines - Líneas.
 * @returns {number} Suma de cantidad × precio unitario.
 */
export const total = (lines) => lines.reduce((sum, l) => sum + (Number(l.cantidad) || 0) * (Number(l.precio_unitario) || 0), 0);
/**
 * Línea vacía de solicitud.
 * @returns {{descripcion: string, cantidad: number, precio_unitario: number}} Línea.
 */
export const emptyLine = () => ({ descripcion: '', cantidad: 1, precio_unitario: 0 });

// Mirrors the server rules for a quick error; the server stays the authority.
/**
 * Valida el borrador en cliente (el servidor sigue siendo la autoridad).
 * @param {{justificacion: string, detalles: Array<{descripcion: string, cantidad: number, precio_unitario: number}>}} draft - Borrador.
 * @returns {Object} El mismo borrador.
 * @throws {Error} Si falta justificación, líneas o hay datos inválidos.
 */
export function validate(draft) {
  if (!draft.justificacion.trim()) throw new Error('Completa el campo justificación.');
  if (!draft.detalles.length) throw new Error('Agrega por lo menos un título.');
  for (const l of draft.detalles) {
    if (!l.descripcion.trim()) throw new Error('Completa el título de cada línea.');
    if (!Number.isInteger(l.cantidad) || l.cantidad < 1) throw new Error('La cantidad de cada título debe ser un entero positivo.');
    if (!Number.isFinite(l.precio_unitario) || l.precio_unitario < 0) throw new Error('Introduce un precio unitario válido.');
  }
  return draft;
}

/**
 * Crea una solicitud. Llama a POST /api/compras.
 * @param {{justificacion: string, detalles: Object[]}} draft - Borrador.
 * @returns {Promise<Object>} Solicitud creada (201).
 */
export const create = (draft) => api.post('/compras', { justificacion: draft.justificacion, detalles: draft.detalles });

// Creates the request, then sends it. If sending fails, draft.id lets the caller retry only the send.
/**
 * Crea la solicitud y la envía; si el envío falla, `draft.id` permite reintentar solo el envío. Llama a POST /api/compras y POST /api/compras/:id/enviar.
 * @param {{id?: number, justificacion: string, detalles: Object[]}} draft - Borrador (se le asigna `id`).
 * @returns {Promise<Object>} Solicitud enviada.
 */
export async function createAndSend(draft) {
  if (!draft.id) draft.id = (await create(draft)).id_solicitud;
  return send(draft.id);
}

// Lines still to receive (ordered - received).
/**
 * Cantidad aún por recibir de una línea.
 * @param {{cantidad: number, cantidad_recibida?: number}} l - Línea.
 * @returns {number} Pedido menos recibido.
 */
export const pending = (l) => l.cantidad - (l.cantidad_recibida || 0);
/**
 * Indica si se puede recibir pedido: solicitud enviada con líneas pendientes.
 * @param {{estado: string, detalles: Object[]}} s - Solicitud.
 * @returns {boolean}
 */
export const canReceive = (s) => s.estado === 'enviada' && s.detalles.some((l) => pending(l) > 0);
/**
 * Indica si se puede cancelar: pendiente o enviada, sin cantidades recibidas.
 * @param {{estado: string, detalles: Object[]}} s - Solicitud.
 * @returns {boolean}
 */
export const canCancel = (s) => ['pendiente', 'enviada'].includes(s.estado)
  && !s.detalles.some((l) => l.cantidad_recibida > 0);

// Builds the reception payload from the form values (cant_<id_detalle> inputs).
/**
 * Construye el payload de recepción desde los valores del formulario (inputs `cant_<id_detalle>`).
 * @param {Object} data - Valores del formulario (factura_folio, factura_total, fecha_recepcion, cant_*).
 * @param {{detalles: Object[]}} s - Solicitud a recibir.
 * @returns {{factura_folio: string, factura_total: number, lineas: Object[], fecha_recepcion?: string}} Payload.
 * @throws {Error} Si el folio, el monto o las cantidades son inválidos.
 */
export function receptionPayload(data, s) {
  const lineas = s.detalles.map((l) => ({ id_detalle: l.id_detalle, cantidad_recibida: Number(data['cant_' + l.id_detalle] || 0) }));
  if (!data.factura_folio.trim() || data.factura_folio.trim().length < 3) throw new Error('El folio de factura debe tener al menos 3 caracteres.');
  if (!(Number(data.factura_total) >= 0) || data.factura_total === '') throw new Error('Introduce un monto de factura válido.');
  if (lineas.some((l) => !Number.isInteger(l.cantidad_recibida) || l.cantidad_recibida < 0)) throw new Error('Las cantidades recibidas deben ser enteros positivos.');
  const payload = { factura_folio: data.factura_folio.trim(), factura_total: Number(data.factura_total), lineas };
  if (data.fecha_recepcion) payload.fecha_recepcion = data.fecha_recepcion;
  return payload;
}
