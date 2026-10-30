/**
 * @module modules/espera/controller — rutas y manejadores de la lista de espera (capa controller; une model y view).
 */
import { listPage, editPage } from '/js/core/crud.js';
import { setFlash } from '/js/core/ui.js';
import { confirmAction, onAction, count } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Estado de filtros del listado de personal (se conserva entre renderizados).
 * @type {{q: string, estado: string}}
 */
const filters = { q: '', estado: '' };

/**
 * Enlaza el botón Cancelar (con confirmación) de las tablas de espera.
 * @param {HTMLElement} main - Contenedor de la página.
 * @param {Object} opts - Opciones.
 * @param {function(): (void|Promise<void>)} opts.refresh - Recarga la vista tras cancelar.
 * @returns {void}
 */
function bindCancel(main, { refresh }) {
  onAction(main, {
    cancelar: async (button) => {
      const ok = await confirmAction({
        title: 'Cancelar solicitud',
        message: `Se cancelará la solicitud de espera de ${button.dataset.nombre}.`,
        confirmLabel: 'Cancelar solicitud',
      });
      if (!ok) return;
      await model.cancel(button.dataset.id);
      setFlash('Solicitud cancelada.');
      await refresh();
    },
  });
}

/**
 * Vista `espera` (personal): listado con búsqueda y filtro de estado.
 * @param {Object} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function list(params, ctx) {
  const refresh = () => list(params, ctx);
  const main = await listPage(ctx, {
    markup: view.listPage(filters), filters, load: model.list, render: view.rows, summary: view.summary,
  });
  if (main) bindCancel(main, { refresh });
}

/**
 * Vista `espera/nueva` (personal): alta en la lista; admite prellenar `matricula` e `id_libro` desde la query (enlace desde préstamos).
 * @param {Object} params - Parámetros de ruta.
 * @param {{query: Object}} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function add(params, ctx) {
  // Prestamos enlaza a "#/espera?matricula=..&id_libro=.." para prellenar el alta.
  const values = { matricula: ctx.query.matricula || '', id_libro: ctx.query.id_libro || '' };
  const libros = await model.libros();
  editPage(ctx, {
    markup: view.form(values, libros),
    formId: 'espera-form',
    save: model.create,
    message: 'Usuario añadido a la lista de espera.',
    redirect: () => 'espera',
  });
}

/**
 * Vista `espera/unirse/:id_libro` (usuario): confirmación para unirse a la espera de un libro.
 * @param {{id_libro: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function join(params, ctx) {
  const libro = await model.libro(params.id_libro);
  editPage(ctx, {
    markup: view.joinPage(libro),
    formId: 'join-form',
    save: () => model.join(params.id_libro),
    message: 'Quedaste en la lista de espera.',
    redirect: () => 'espera/mias',
  });
}

/**
 * Vista `espera/mias` (usuario): solicitudes propias con opción de cancelar.
 * @param {Object} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function mine(params, ctx) {
  const refresh = () => mine(params, ctx);
  const main = await listPage(ctx, {
    markup: view.minePage(), load: model.mine, render: view.mineRows, summary: (items) => count(items.length),
  });
  if (main) bindCancel(main, { refresh });
}

/**
 * Rutas del módulo (hash `#/<path>`).
 * - `espera` (permiso `espera`): listado, o alta si la query trae `matricula`/`id_libro`.
 * - `espera/nueva` (permiso `espera`): alta.
 * - `espera/mias` (sesión iniciada, sin permiso específico): mis solicitudes.
 * - `espera/unirse/:id_libro` (sesión iniciada): unirse a la espera.
 * @type {Array<{path: string, perm?: string, section: string, action: function}>}
 */
export const routes = [
  { path: 'espera', perm: 'espera', section: 'espera', action: (params, ctx) => (ctx.query.matricula || ctx.query.id_libro ? add(params, ctx) : list(params, ctx)) },
  { path: 'espera/nueva', perm: 'espera', section: 'espera', action: add },
  { path: 'espera/mias', section: 'espera', action: mine },
  { path: 'espera/unirse/:id_libro', section: 'espera', action: join },
];
