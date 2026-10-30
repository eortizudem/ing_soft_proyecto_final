/** @module core/crud — flujos genéricos de controlador compartidos por los módulos: listados, edición y baja/reactivación. */
import { $, setFlash, showError, clearError } from './ui.js';
import { go } from './router.js';
import { bindToolbar, bindForm, confirmAction, onAction } from '/js/components/index.js';

/**
 * Página de listado: pinta `markup` (page + toolbar() + resultsPanel()/resultsList()), enlaza la
 * toolbar y rellena #results con render(items) y #count con summary(items). Los errores van a #alert.
 * `filters` es un objeto a nivel de módulo para que los filtros sobrevivan a la navegación.
 * @param {Object} ctx - Contexto del router (`ctx.render` devuelve null si la ruta quedó obsoleta).
 * @param {Object} opts - Opciones.
 * @param {Safe|string} opts.markup - Vista completa de la página.
 * @param {Object} [opts.filters] - Estado de filtros compartido y mutable (se pasa a `load` como copia).
 * @param {function(Object): Promise<Array<Object>>} opts.load - Obtiene los elementos según los filtros.
 * @param {function(Array<Object>): (Safe|string)} opts.render - Convierte los elementos en HTML.
 * @param {function(Array<Object>): string} [opts.summary] - Texto del contador #count.
 * @param {number} [opts.debounce] - Retardo (ms) de la búsqueda en la toolbar.
 * @returns {Promise<?HTMLElement>} El <main> de la página, o null si la ruta quedó obsoleta.
 * @example
 * listPage(ctx, { markup: view(filters), filters, load: (f) => api.get('/libros' + query(f)),
 *   render: tablaLibros, summary: (items) => count(items.length, 'libro') });
 */
export async function listPage(ctx, { markup, filters = {}, load, render, summary, debounce }) {
  const main = ctx.render(markup);
  if (!main) return null;
  const results = $('#results', main);
  const counter = $('#count', main);
  const refresh = async () => {
    results.setAttribute('aria-busy', 'true');
    clearError();
    try {
      const items = await load({ ...filters });
      results.innerHTML = String(render(items));
      if (counter && summary) counter.textContent = summary(items);
    } catch (err) {
      showError(err);
    } finally {
      results.removeAttribute('aria-busy');
    }
  };
  const bar = $('[data-toolbar]', main);
  if (bar) bindToolbar(bar, refresh, { state: filters, debounce });
  await refresh();
  return main;
}

/**
 * Página de edición/alta: pinta el formulario, guarda con save(data), muestra `message` como flash
 * y navega a redirect(saved).
 * @param {Object} ctx - Contexto del router.
 * @param {Object} opts - Opciones.
 * @param {Safe|string} opts.markup - Vista con el formulario.
 * @param {string} opts.formId - Id del <form> dentro de la vista (sin `#`).
 * @param {function(Object): Promise<any>} opts.save - Persiste los datos serializados del formulario.
 * @param {string} opts.message - Mensaje flash de éxito.
 * @param {function(any): string} opts.redirect - Devuelve la ruta destino a partir del resultado de `save`.
 * @returns {?HTMLElement} El <main> de la página, o null si la ruta quedó obsoleta.
 * @example
 * editPage(ctx, { markup: formView(...), formId: 'libro-form', save: (d) => api.post('/libros', d),
 *   message: 'Libro creado.', redirect: (libro) => `libros/${libro.id}` });
 */
export function editPage(ctx, { markup, formId, save, message, redirect }) {
  const main = ctx.render(markup);
  if (!main) return null;
  bindForm($(`#${formId}`, main), {
    onSubmit: async (data) => {
      const saved = await save(data);
      setFlash(message);
      go(redirect(saved));
    },
  });
  return main;
}

/**
 * Enlaza el botón [data-action="toggle"] (baja/reactivar): modal de confirmación -> run() ->
 * flash success(result) -> refresh().
 * @param {HTMLElement} main - Contenedor de la página con el botón.
 * @param {Object} opts - Opciones.
 * @param {function(): Object} opts.confirm - Devuelve las opciones de `confirmAction` (se evalúa al pulsar).
 * @param {function(): Promise<any>} opts.run - Ejecuta la acción en el servidor.
 * @param {function(any): string} opts.success - Mensaje flash a partir del resultado de `run`.
 * @param {function(): Promise<any>} opts.refresh - Recarga la vista tras la acción.
 * @returns {void}
 */
export function bindToggle(main, { confirm, run, success, refresh }) {
  onAction(main, {
    toggle: async () => {
      if (!(await confirmAction(confirm()))) return;
      const result = await run();
      setFlash(success(result));
      await refresh();
    },
  });
}
