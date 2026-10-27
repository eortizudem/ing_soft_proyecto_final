// Waitlist HTML (pure functions: data -> components).
import { html } from '/js/core/ui.js';
import { page, btn, toolbar, resultsPanel, dataTable, statusBadge, formView, submitButton, notice,
  labelItems, count, datetime, actions } from '/js/components/index.js';

const ACTIVE = ['en_espera', 'notificado'];
const isActive = (e) => ACTIVE.includes(e.estado);

export const listPage = (filters) => page({
  title: 'Lista de espera',
  desc: 'Solicitudes por libro sin ejemplares disponibles, en orden de llegada.',
  actions: btn({ label: 'Añadir a la lista', href: 'espera/nueva', variant: 'primary' }),
  body: html`
  ${toolbar({
    search: { name: 'q', label: 'Buscar', value: filters.q, placeholder: 'Usuario, matrícula o libro' },
    filters: [{ name: 'estado', label: 'Estado', value: filters.estado,
      options: [['', 'Todos los estados'], ...labelItems('listaEspera')] }],
  })}
  ${resultsPanel()}`,
});

export const summary = (items) => count(items.length) + ` · ${items.filter(isActive).length} activas`;

const libroCell = (e) => html`${e.libro.titulo} <span class="muted">(${e.libro.clave})</span>`;

export const rows = (items) => dataTable({
  rows: items,
  empty: { text: 'No hay solicitudes con estos filtros.' },
  columns: [
    { label: 'Libro', render: libroCell },
    { label: 'Usuario', render: (e) => `${e.usuario.nombre_completo} (${e.usuario.matricula})` },
    { label: 'Posición', align: 'center', render: (e) => (isActive(e) ? e.posicion : '—') },
    { label: 'Estado', render: (e) => statusBadge('listaEspera', e.estado) },
    { label: 'Solicitud', render: (e) => datetime(e.fecha_solicitud) },
    { label: 'Recoger antes de', render: (e) => datetime(e.fecha_limite_recoger) || '—' },
    { label: 'Acciones', render: (e) => (isActive(e)
      ? btn({ label: 'Cancelar', action: 'cancelar', variant: 'danger', data: { id: e.id_espera, nombre: e.usuario.nombre_completo } })
      : '') },
  ],
});

const libroLabel = (l) => `${l.titulo} (${l.clave}) · ${l.disponibles ? l.disponibles + ' disponible(s)' : 'sin ejemplares'}`;

export const form = (values, libros) => page({
  title: 'Añadir a la lista de espera',
  desc: 'Solo se admiten libros de préstamo externo sin ejemplares disponibles.',
  body: formView({
    id: 'espera-form',
    fields: [
      { name: 'matricula', label: 'Matrícula / nómina', value: values.matricula, required: true, maxlength: 24 },
      { name: 'id_libro', label: 'Libro', type: 'select', required: true, value: values.id_libro,
        options: [['', 'Selecciona un libro'], ...libros.map((l) => [l.id_libro, libroLabel(l)])] },
    ],
    actions: [btn({ label: 'Cancelar', href: 'espera', variant: 'link' }), submitButton('Añadir a la lista')],
  }),
});

export const joinPage = (libro) => page({
  title: 'Unirme a la lista de espera',
  desc: 'Te avisaremos por correo cuando haya un ejemplar; se apartará para ti 2 días hábiles.',
  body: html`
  ${notice({ text: `${libro.titulo} (${libro.clave}) · ${libro.disponibles} ejemplar(es) disponible(s).` })}
  ${formView({
    id: 'join-form', fields: [],
    actions: [btn({ label: 'Cancelar', href: 'buscar', variant: 'link' }), submitButton('Unirme a la lista')],
  })}`,
});

export const minePage = () => page({
  title: 'Mis solicitudes de espera',
  desc: 'Libros que esperas y el plazo para recogerlos cuando te avisamos.',
  body: html`${resultsPanel()}${actions([btn({ label: 'Buscar libros', href: 'buscar', variant: 'link' })])}`,
});

export const mineRows = (items) => dataTable({
  rows: items,
  empty: { title: 'Sin solicitudes', text: 'Aún no estás en ninguna lista de espera.' },
  columns: [
    { label: 'Libro', render: libroCell },
    { label: 'Posición', align: 'center', render: (e) => (isActive(e) ? e.posicion : '—') },
    { label: 'Estado', render: (e) => statusBadge('listaEspera', e.estado) },
    { label: 'Recoger antes de', render: (e) => datetime(e.fecha_limite_recoger) || '—' },
    { label: 'Acciones', render: (e) => (isActive(e)
      ? btn({ label: 'Cancelar', action: 'cancelar', variant: 'danger', data: { id: e.id_espera, nombre: e.libro.titulo } })
      : '') },
  ],
});
