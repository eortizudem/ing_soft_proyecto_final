// Notifications HTML (pure functions: data -> components).
import { html } from '/js/core/ui.js';
import { page, btn, badge, toolbar, resultsPanel, dataTable, labelItems, label, count, datetime } from '/js/components/index.js';

export const PERIODOS = [['', 'Todo el historial'], ['1', 'Hoy'], ['7', 'Últimos 7 días'], ['30', 'Últimos 30 días']];

const toolbarFor = (filters) => toolbar({
  search: { name: 'q', label: 'Buscar por persona o texto', value: filters.q, placeholder: 'Matrícula, nombre, correo o asunto' },
  filters: [
    { name: 'canal', label: 'Canal', value: filters.canal, options: [['', 'Todos los canales'], ...labelItems('canal')] },
    { name: 'periodo', label: 'Periodo', value: filters.periodo, options: PERIODOS },
  ],
});

export const listPage = (filters, mine = false) => page({
  title: mine ? 'Mis notificaciones' : 'Notificaciones',
  desc: 'Avisos simulados: se registran aquí en lugar de enviarse a un proveedor real.',
  actions: mine ? '' : btn({ label: 'Mis notificaciones', href: 'notificaciones/mias', variant: 'link' }),
  body: html`${toolbarFor(filters)}${resultsPanel()}`,
});

export const summary = (items) => count(items.length, 'notificación(es)');

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
