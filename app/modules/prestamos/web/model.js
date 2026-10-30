/**
 * @module modules/prestamos/model — llamadas a la API de préstamos y políticas (sin HTML ni DOM; capa model).
 */
import { api, query, LIST_LIMIT } from '/js/core/api.js';

/**
 * Codifica un valor para usarlo como segmento de URL.
 * @param {string|number} value - Identificador.
 * @returns {string} Valor con `encodeURIComponent`.
 */
const id = (value) => encodeURIComponent(value);

/**
 * GET /api/prestamos — lista préstamos con filtros (tope `LIST_LIMIT`).
 * @param {Object} [filters] - Filtros.
 * @param {string} [filters.estado] - 'activo', 'vencido', 'devuelto' o vacío.
 * @param {string} [filters.q] - Búsqueda libre (matrícula, nombre, clave, título, folio).
 * @param {string} [filters.matricula] - Matrícula exacta.
 * @returns {Promise<Array<Object>>} Préstamos con `usuario`, `libro` y `multa_estimada`.
 */
export const list = ({ estado = '', q = '', matricula = '' } = {}) => api.get('/prestamos' + query({ estado, q, matricula, limite: LIST_LIMIT }));
/**
 * GET /api/prestamos/:id — detalle con renovaciones y adeudos.
 * @param {string|number} value - Id del préstamo.
 * @returns {Promise<Object>} Préstamo detallado.
 */
export const get = (value) => api.get('/prestamos/' + id(value));
/**
 * GET /api/prestamos/:id/recibo — datos del recibo de préstamo (RF-19).
 * @param {string|number} value - Id del préstamo.
 * @returns {Promise<Object>} Recibo con folio, usuario, libro, política y avisos.
 */
export const recibo = (value) => api.get(`/prestamos/${id(value)}/recibo`);
/**
 * POST /api/prestamos/:id/renovar — renueva el préstamo (RN-02/RN-06).
 * @param {string|number} value - Id del préstamo.
 * @returns {Promise<Object>} `{ prestamo, renovacion: { nueva_fecha_vencimiento } }`.
 */
export const renovar = (value) => api.post(`/prestamos/${id(value)}/renovar`);
/**
 * POST /api/prestamos/:id/devolver — registra la devolución.
 * @param {string|number} value - Id del préstamo.
 * @returns {Promise<Object>} `{ prestamo, dias_retraso, adeudo, espera_notificada }`.
 */
export const devolver = (value) => api.post(`/prestamos/${id(value)}/devolver`);
/**
 * POST /api/prestamos/:id/recibo/enviar — reenvía el recibo por los canales indicados.
 * @param {string|number} value - Id del préstamo.
 * @param {Array<string>} canales - 'email' y/o 'whatsapp'.
 * @returns {Promise<Object>} `{ enviados }`.
 */
export const enviarRecibo = (value, canales) => api.post(`/prestamos/${id(value)}/recibo/enviar`, { canales });

/**
 * POST /api/prestamos/validar — valida RN-01 sin registrar el préstamo.
 * @param {Object} values - Datos del formulario.
 * @param {string} values.matricula - Matrícula o nómina del usuario.
 * @param {string} values.clave - Clave del libro.
 * @returns {Promise<Object>} `{ autorizado, motivos, usuario, libro, dias_prestamo, fecha_vencimiento_estimada }`.
 */
export const validar = ({ matricula, clave }) => api.post('/prestamos/validar', { matricula: matricula.trim(), clave: clave.trim() });

// Form values (checkboxes canal_email / canal_whatsapp) -> API payload.
/**
 * POST /api/prestamos — registra un préstamo; convierte los checkboxes de canal en la lista `canales`.
 * @param {Object} data - Valores del formulario.
 * @param {string} data.matricula - Matrícula o nómina.
 * @param {string} data.clave - Clave del libro.
 * @param {boolean} [data.canal_email] - Enviar recibo por correo.
 * @param {boolean} [data.canal_whatsapp] - Enviar recibo por WhatsApp.
 * @returns {Promise<Object>} `{ prestamo, recibo }`.
 */
export const crear = (data) => api.post('/prestamos', {
  matricula: data.matricula.trim(),
  clave: data.clave.trim(),
  canales: [data.canal_email && 'email', data.canal_whatsapp && 'whatsapp'].filter(Boolean),
});

/**
 * GET /api/politicas — lista las políticas de préstamo por rol.
 * @returns {Promise<Array<Object>>} Políticas.
 */
export const politicas = () => api.get('/politicas');
/**
 * Busca una política por id dentro de GET /api/politicas (no hay endpoint individual).
 * @param {string|number} value - Id de la política.
 * @returns {Promise<Object|undefined>} Política o undefined si no existe.
 */
export const politica = async (value) => (await politicas()).find((p) => String(p.id_politica) === String(value));
/**
 * PUT /api/politicas/:id — guarda una política (permiso `perfiles`).
 * @param {string|number} value - Id de la política.
 * @param {Object} data - Valores del formulario (se convierten a número).
 * @param {string|number} data.dias_prestamo - Días hábiles de préstamo.
 * @param {string|number} data.max_libros - Máximo de libros simultáneos.
 * @param {string|number} data.max_renovaciones - Máximo de renovaciones.
 * @param {string|number} data.multa_diaria - Multa por día hábil (MXN).
 * @returns {Promise<Object>} Política actualizada.
 */
export const savePolitica = (value, data) => api.put('/politicas/' + id(value), {
  dias_prestamo: Number(data.dias_prestamo),
  max_libros: Number(data.max_libros),
  max_renovaciones: Number(data.max_renovaciones),
  multa_diaria: Number(data.multa_diaria),
});
