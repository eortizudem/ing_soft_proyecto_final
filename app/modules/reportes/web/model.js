/** @module modules/reportes/model — llamadas a la API de reportes y ayudas de filtros/PDF */
import { api, query } from '/js/core/api.js';
import { datetime } from '/js/components/index.js';

/**
 * Tipos de reporte y su etiqueta.
 * @type {Object<string, string>}
 */
export const TYPES = {
  catalogo_completo: 'Catálogo completo',
  catalogo_activo: 'Catálogo activo',
  usuarios: 'Listado de usuarios',
  con_adeudos: 'Alumnos con adeudos (libros vencidos y multas)',
  inventario_estante: 'Inventario por estante',
  prestamos_vencidos: 'Préstamos vencidos',
  prestamos: 'Préstamos por periodo',
  indicadores: 'Indicadores (asistente, inventario, préstamos)',
  errores: 'Errores del sistema (del servidor y del navegador)',
};

// Permiso adicional a `reportes` (espejo del backend): el tipo se oculta sin él.
/**
 * Permiso adicional a `reportes` por tipo (espejo del backend).
 * @type {Object<string, string>}
 */
export const EXTRA_PERMISSION = { usuarios: 'usuarios', con_adeudos: 'prestamos', prestamos_vencidos: 'prestamos', prestamos: 'prestamos' };

// Filtros opcionales que acepta cada tipo (el resto se ignora).
/**
 * Filtros opcionales que acepta cada tipo.
 * @type {Object<string, string[]>}
 */
export const FILTERS = {
  con_adeudos: ['incluir_docentes'],
  inventario_estante: ['planta', 'pasillo', 'librero', 'tema'],
  prestamos: ['desde', 'hasta'],
  indicadores: ['desde', 'hasta'],
  errores: ['desde', 'hasta'],
};

// Query string de los filtros del tipo (solo los que aplican y no están vacíos).
/**
 * Filtros del tipo que aplican y no están vacíos.
 * @param {string} tipo - Tipo de reporte.
 * @param {Object} [values] - Valores capturados.
 * @returns {Object<string, string>} Parámetros de consulta.
 */
export const filterQuery = (tipo, values = {}) =>
  Object.fromEntries((FILTERS[tipo] || []).map((k) => [k, values[k]]).filter(([, v]) => v && v !== 'false'));

// formato: pantalla | pdf | impresion (each call is logged by the server)
/**
 * Genera el reporte (cada llamada se registra en el servidor). Llama a GET /api/reportes/:tipo.
 * @param {string} tipo - Tipo de reporte.
 * @param {'pantalla'|'pdf'|'impresion'} formato - Formato solicitado.
 * @param {Object} [filters] - Filtros capturados.
 * @returns {Promise<{tipo: string, generado: string, generado_por: string, columnas: string[], filas: Array[], total: number}>} Reporte.
 */
export const fetchReport = (tipo, formato, filters = {}) =>
  api.get(`/reportes/${encodeURIComponent(tipo)}${query({ ...filterQuery(tipo, filters), formato })}`);

// RF-28: aviso único a Servicios Escolares con las matrículas de los alumnos con adeudos.
/**
 * RF-28: aviso a Servicios Escolares con las matrículas con adeudos. Llama a POST /api/reportes/con_adeudos/aviso.
 * @param {boolean} [incluir_docentes] - Incluir docentes.
 * @returns {Promise<{enviados: number, matriculas: string[]}>} Resultado.
 */
export const sendDebtorNotice = (incluir_docentes = false) => api.post('/reportes/con_adeudos/aviso', { incluir_docentes });

// Ruta `reportes/<tipo>?a=b`; el router entrega los filtros en ctx.query.
/**
 * Ruta del cliente `reportes/<tipo>?filtros`.
 * @param {string} tipo - Tipo de reporte.
 * @param {Object} [values] - Valores de filtros.
 * @returns {string} Ruta hash sin '#'.
 */
export const reportPath = (tipo, values = {}) => `reportes/${tipo}${query(filterQuery(tipo, values))}`;

// Plain-text lines for the hand-written PDF.
/**
 * Líneas de texto plano para el PDF.
 * @param {{tipo: string, generado: string, generado_por: string, total: number, columnas: string[], filas: Array[]}} report - Reporte.
 * @returns {string[]} Líneas.
 */
export function pdfLines(report) {
  const lines = [
    'LibriGest - Universidad Ducky',
    TYPES[report.tipo] || report.tipo,
    `Generado: ${datetime(report.generado)} | por: ${report.generado_por} | ${report.total} registros`,
    '',
    report.columnas.join(' | '),
    '',
  ];
  for (const row of report.filas) lines.push(row.map((c) => c ?? '').join(' | '), '');
  return lines;
}
