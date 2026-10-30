/**
 * @module modules/espera/view — HTML de la lista de espera (funciones puras: datos -> componentes; capa view).
 */
import { html } from '/js/core/ui.js';
import { page, btn, toolbar, resultsPanel, dataTable, statusBadge, formView, submitButton, notice,
  labelItems, count, datetime, actions } from '/js/components/index.js';

/**
 * Estados que ocupan posición en la fila.
 * @type {Array<string>}
 */
const ACTIVE = ['en_espera', 'notificado'];
/**
 * Indica si una entrada de espera sigue activa.
 * @param {{estado: string}} e - Entrada de espera.
 * @returns {boolean} True si está 'en_espera' o 'notificado'.
 */
const isActive = (e) => ACTIVE.includes(e.estado);

/**
 * Página del listado de espera (personal) con búsqueda y filtro de estado.
 * @param {{q: string, estado: string}} filters - Filtros actuales.
 * @returns {Safe} Página con panel de resultados vacío.
 */
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

/**
 * Texto del contador del listado.
 * @param {Array<Object>} items - Entradas cargadas.
 * @returns {string} Total y número de activas.
 */
export const summary = (items) => count(items.length) + ` · ${items.filter(isActive).length} activas`;

/**
 * Celda de libro con título y clave.
 * @param {{libro: {titulo: string, clave: string}}} e - Entrada de espera.
 * @returns {Safe} HTML de la celda.
 */
const libroCell = (e) => html`${e.libro.titulo} <span class="muted">(${e.libro.clave})</span>`;

/**
 * Tabla de espera del personal: libro, usuario, posición, estado, fechas y botón Cancelar (solo activas).
 * @param {Array<Object>} items - Entradas con `libro`, `usuario`, `posicion`, `estado`, `fecha_solicitud`, `fecha_limite_recoger`, `id_espera`.
 * @returns {Safe} Tabla HTML.
 */
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

/**
 * Etiqueta de opción de libro con su disponibilidad.
 * @param {{titulo: string, clave: string, disponibles: number}} l - Libro.
 * @returns {string} Texto de la opción.
 */
const libroLabel = (l) => `${l.titulo} (${l.clave}) · ${l.disponibles ? l.disponibles + ' disponible(s)' : 'sin ejemplares'}`;

/**
 * Formulario de alta en la lista de espera (matrícula y libro).
 * @param {{matricula: string, id_libro: string}} values - Valores iniciales.
 * @param {Array<Object>} libros - Libros candidatos (`id_libro`, `titulo`, `clave`, `disponibles`).
 * @returns {Safe} Página.
 */
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

/**
 * Página de confirmación para que el usuario se una a la espera de un libro.
 * @param {{titulo: string, clave: string, disponibles: number}} libro - Libro elegido.
 * @returns {Safe} Página.
 */
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

/**
 * Página 'Mis solicitudes de espera' (panel de resultados y enlace a búsqueda).
 * @returns {Safe} Página.
 */
export const minePage = () => page({
  title: 'Mis solicitudes de espera',
  desc: 'Libros que esperas y el plazo para recogerlos cuando te avisamos.',
  body: html`${resultsPanel()}${actions([btn({ label: 'Buscar libros', href: 'buscar', variant: 'link' })])}`,
});

/**
 * Tabla de solicitudes propias: libro, posición, estado, plazo y botón Cancelar (solo activas).
 * @param {Array<Object>} items - Entradas con `libro`, `posicion`, `estado`, `fecha_limite_recoger`, `id_espera`.
 * @returns {Safe} Tabla HTML.
 */
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
