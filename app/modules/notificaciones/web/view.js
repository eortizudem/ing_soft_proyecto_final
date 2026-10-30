/** @module modules/notificaciones/view — vistas de notificaciones simuladas (funciones puras datos -> componentes). */
import { html } from '/js/core/ui.js';
import { page, btn, badge, toolbar, resultsPanel, dataTable, labelItems, label, count, datetime } from '/js/components/index.js';

/**
 * Opciones del filtro de periodo: `[valor en días, etiqueta]`.
 * @type {Array<[string, string]>}
 */
export const PERIODOS = [['', 'Todo el historial'], ['1', 'Hoy'], ['7', 'Últimos 7 días'], ['30', 'Últimos 30 días']];

/**
 * Barra de búsqueda y filtros (canal, periodo).
 * @param {{q: string, canal: string, periodo: string}} filters - valores actuales.
 * @returns {object} barra de herramientas.
 */
const toolbarFor = (filters) => toolbar({
  search: { name: 'q', label: 'Buscar por persona o texto', value: filters.q, placeholder: 'Matrícula, nombre, correo o asunto' },
  filters: [
    { name: 'canal', label: 'Canal', value: filters.canal, options: [['', 'Todos los canales'], ...labelItems('canal')] },
    { name: 'periodo', label: 'Periodo', value: filters.periodo, options: PERIODOS },
  ],
});

/**
 * Pantalla de lista de notificaciones (del personal, o propias si `mine`).
 * @param {{q: string, canal: string, periodo: string}} filters - valores actuales de filtros.
 * @param {boolean} [mine=false] - `true` para "Mis notificaciones".
 * @returns {object} página.
 */
export const listPage = (filters, mine = false) => page({
  title: mine ? 'Mis notificaciones' : 'Notificaciones',
  desc: 'Avisos simulados: se registran aquí en lugar de enviarse a un proveedor real.',
  actions: mine ? '' : btn({ label: 'Mis notificaciones', href: 'notificaciones/mias', variant: 'link' }),
  body: html`${toolbarFor(filters)}${resultsPanel()}`,
});

/**
 * Texto de resumen con el total de resultados.
 * @param {Array<object>} items - avisos cargados.
 * @returns {string} p. ej. "3 notificación(es)".
 */
export const summary = (items) => count(items.length, 'notificación(es)');

/**
 * Tabla de avisos simulados (siempre con estado "Simulado"; la columna Usuario solo para el personal).
 * @param {Array<{fecha: string, canal: string, usuario: {matricula: string, nombre_completo: string}, destino: string, asunto: string, cuerpo: string}>} items - avisos.
 * @param {boolean} [mine=false] - oculta la columna Usuario.
 * @returns {object} tabla de datos.
 */
export const rows = (items, mine = false) => dataTable({
  rows: items,
  empty: { text: 'No hay notificaciones con esos filtros.' },
  columns: [
    { label: 'Fecha', render: (n) => datetime(n.fecha) },
    { label: 'Canal', render: (n) => label('canal', n.canal) },
    ...(mine ? [] : [{ label: 'Usuario', render: (n) => `${n.usuario.matricula} · ${n.usuario.nombre_completo}` }]),
    { label: 'Destino', key: 'destino' },
    { label: 'Asunto', key: 'asunto' },
    { label: 'Mensaje', key: 'cuerpo' },
    { label: 'Estado', render: () => badge('Simulado', 'warn') },
  ],
});
