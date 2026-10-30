/** @module modules/catalogo/controller — rutas y manejo de eventos de catálogo, búsqueda pública, ubicación e importación */
import * as session from '/js/core/session.js';
import { $, setFlash, showError } from '/js/core/ui.js';
import { listPage, editPage, bindToggle } from '/js/core/crud.js';
import { onAction, bindForm, bindFileToText, confirmAction, printHtml } from '/js/components/index.js';
import { downloadPdf } from '/js/core/pdf.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Filtros vigentes de la lista administrativa del catálogo.
 * @type {Object}
 */
const filters = { q: '', campo: '', tema: '', estado: '', tipo_uso: '', disponibilidad: '' };

/**
 * Ruta `#/catalogo` (permiso `catalogo`): lista administrativa de libros con filtros.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router (render, query).
 * @returns {Promise<void>}
 */
async function list(params, ctx) {
  const themes = await model.themes();
  await listPage(ctx, {
    markup: view.listPage(themes, filters),
    filters,
    load: model.list,
    render: view.rows,
    summary: view.summary,
  });
}

/**
 * Rutas `#/libros/nuevo` y `#/libros/:id/editar` (permiso `catalogo`): formulario de ficha.
 * Con `?id_detalle=N` precarga datos de la compra recibida pendiente.
 * @param {{id?: string}} params - Parámetros de ruta; `id` si se edita.
 * @param {Object} ctx - Contexto del router (render, query).
 * @returns {Promise<void>}
 */
async function edit(params, ctx) {
  const editing = !!params.id;
  // "#/libros/nuevo?id_detalle=N": book received by Compras; prefill from the pending line.
  const idDetalle = editing ? '' : ctx.query.id_detalle || '';
  const [themes, book, pend] = await Promise.all([model.themes(), editing ? model.get(params.id) : model.emptyBook(),
    idDetalle ? model.pendientes().catch(() => []) : []]);
  const pending = pend.find((p) => String(p.id_detalle) === idDetalle) || null;
  if (pending) Object.assign(book, { titulo: pending.descripcion, ejemplares: pending.cantidad_recibida,
    precio_referencia: Number(pending.precio_unitario) || 0 });
  editPage(ctx, {
    markup: view.form(book, themes, editing, pending),
    formId: 'book-form',
    save: (data) => model.save(editing ? params.id : null, { ...data, id_detalle: pending ? idDetalle : '' }),
    message: 'Ficha bibliográfica guardada correctamente.',
    redirect: (saved) => 'libros/' + saved.id_libro,
  });
}

/**
 * Indica si el usuario en sesión (no visitante) puede unirse a una lista de espera.
 * @returns {boolean}
 */
const canWait = () => !!session.get() && !session.isVisitor();

/**
 * Ruta `#/libros/:id` (permiso `catalogo` o `buscar`): ficha del libro; con permiso `catalogo` agrega ejemplares, baja/reactivar, imprimir/PDF y activar/inactivar.
 * @param {{id: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function detail(params, ctx) {
  const book = await model.get(params.id);
  const canEdit = session.can('catalogo');
  const ejemplares = canEdit ? await model.ejemplares(book.id_libro) : null;
  const main = ctx.render(view.detail(book, { canEdit, canLocate: session.can('buscar'), canWait: canWait(), ejemplares }));
  if (!main || !canEdit) return;
  /**
   * Vuelve a cargar la ficha actual.
   * @returns {Promise<void>}
   */
  const refresh = () => detail(params, ctx);
  /**
   * Obtiene la ficha/etiquetas del libro actual.
   * @returns {Promise<Object>}
   */
  const etiqueta = () => model.etiqueta(book.id_libro);
  onAction(main, {
    /**
     * Acción `baja`: valida el motivo, confirma y da de baja el ejemplar.
     * @param {HTMLElement} button - Botón con `data-id` y `data-etiqueta`.
     * @returns {Promise<void>}
     */
    baja: async (button) => {
      const { id, etiqueta: tag } = button.dataset;
      const select = $(`[data-motivo="${id}"]`, main);
      const motivo = select.value;
      select.removeAttribute('aria-invalid');
      if (!motivo) {
        select.setAttribute('aria-invalid', 'true');
        select.focus();
        return showError('Selecciona el motivo de baja del ejemplar.');
      }
      const ok = await confirmAction({ title: 'Dar de baja ejemplar', confirmLabel: 'Dar de baja',
        message: `¿Deseas dar de baja el ejemplar ${tag}? Quedará registrado el motivo.` });
      if (!ok) return;
      await model.baja(id, motivo);
      setFlash(`Ejemplar ${tag} dado de baja.`);
      await refresh();
    },
    /**
     * Acción `reactivar`: confirma y reactiva el ejemplar.
     * @param {HTMLElement} button - Botón con `data-id` y `data-etiqueta`.
     * @returns {Promise<void>}
     */
    reactivar: async (button) => {
      const { id, etiqueta: tag } = button.dataset;
      if (!(await confirmAction({ title: 'Reactivar ejemplar', confirmLabel: 'Reactivar', variant: 'primary',
        message: `¿Deseas reactivar el ejemplar ${tag}?` }))) return;
      await model.reactivar(id);
      setFlash(`Ejemplar ${tag} reactivado.`);
      await refresh();
    },
    /**
     * Acción `imprimir`: imprime la ficha con etiquetas.
     * @returns {Promise<void>}
     */
    imprimir: async () => printHtml(view.fichaBlock(await etiqueta())),
    /**
     * Acción `pdf`: descarga la ficha con etiquetas como PDF.
     * @returns {Promise<void>}
     */
    pdf: async () => {
      const e = await etiqueta();
      downloadPdf(view.pdfLines(e), `ficha-${e.clave}.pdf`);
    },
  });
  const active = book.estado === 'activo';
  bindToggle(main, {
    confirm: () => ({
      title: active ? 'Confirmar baja de libro' : 'Reactivar libro',
      message: `¿Deseas ${active ? 'dar de baja' : 'reactivar'} «${book.titulo}»? La ficha permanecerá en el catálogo administrativo.`,
      confirmLabel: active ? 'Dar de baja' : 'Reactivar',
    }),
    run: () => model.toggle(book.id_libro),
    success: () => 'Estado del libro actualizado.',
    refresh,
  });
}

/**
 * Ruta `#/libros/pendientes` (permiso `catalogo`): compras recibidas pendientes de catalogar.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function pendientes(params, ctx) {
  await listPage(ctx, { markup: view.pendientesPage(), load: model.pendientes, render: view.pendientesRows });
}

/**
 * Ruta `#/libros/importar` (permiso `catalogo`): importación masiva desde CSV.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router.
 * @returns {void}
 */
function importar(params, ctx) {
  const main = ctx.render(view.importPage());
  if (!main) return;
  bindFileToText($('#archivo', main), $('#csv', main));
  bindForm($('#import-form', main), {
    onSubmit: async (data) => {
      $('#import-result', main).innerHTML = String(view.importResult(await model.importar(data.csv)));
    },
  });
}

// ---- Public search (buscar), mobile mode and floor plan ----
/**
 * Filtros vigentes de la búsqueda pública.
 * @type {Object}
 */
const searchFilters = { q: '', campo: '', tema: '', tipo_uso: '', disponibilidad: '' };

/**
 * Rutas `#/buscar` y `#/movil` (permiso `buscar`): búsqueda pública, en modo escritorio o móvil (`ctx.mobile`).
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router; `mobile` activa el modo móvil.
 * @returns {Promise<void>}
 */
async function search(params, ctx) {
  const mobile = ctx.mobile;
  const themes = mobile ? [] : await model.themes();
  await listPage(ctx, {
    markup: mobile ? view.mobilePage(searchFilters, session.can('asistente')) : view.searchPage(themes, searchFilters, canWait()),
    filters: searchFilters,
    load: model.search,
    render: (books) => view.searchResults(books, canWait()),
  });
}

/**
 * Fábrica de la ruta de ubicación física del libro (`#/libros/:id/ubicacion`, `#/movil/:id`; permiso `buscar`).
 * @param {boolean} mobile - True para la versión móvil.
 * @returns {function(Object, Object): Promise<void>} Acción de ruta.
 */
const locate = (mobile) => async (params, ctx) => {
  ctx.render(view.locationPage(await model.get(params.id), mobile));
};
/**
 * Ruta `#/movil` (permiso `buscar`): búsqueda en modo móvil.
 * @param {Object} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
const searchMobile = (params, ctx) => search(params, Object.assign(ctx, { mobile: true }));
/**
 * Rutas del módulo: catalogo, libros/nuevo, libros/pendientes, libros/importar, libros/:id, libros/:id/editar, buscar, movil, movil/:id, libros/:id/ubicacion.
 * @type {Array<Object>}
 */
export const routes = [
  { path: 'catalogo', perm: 'catalogo', section: 'catalogo', action: list },
  { path: 'libros/nuevo', perm: 'catalogo', section: 'catalogo', action: edit },
  { path: 'libros/pendientes', perm: 'catalogo', section: 'catalogo', action: pendientes },
  { path: 'libros/importar', perm: 'catalogo', section: 'catalogo', action: importar },
  { path: 'libros/:id', perm: ['catalogo', 'buscar'], section: 'catalogo', action: detail },
  { path: 'libros/:id/editar', perm: 'catalogo', section: 'catalogo', action: edit },
  { path: 'buscar', perm: 'buscar', section: 'buscar', action: search },
  { path: 'movil', perm: 'buscar', bare: true, action: searchMobile },
  { path: 'movil/:id', perm: 'buscar', bare: true, action: locate(true) },
  { path: 'libros/:id/ubicacion', perm: 'buscar', section: 'buscar', action: locate(false) },
];
