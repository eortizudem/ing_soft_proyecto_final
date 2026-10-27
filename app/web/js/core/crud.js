// Generic controller flows shared by modules: list pages, edit pages and toggle (baja/reactivar).
import { $, setFlash, showError, clearError } from './ui.js';
import { go } from './router.js';
import { bindToolbar, bindForm, confirmAction, onAction } from '/js/components/index.js';

/**
 * listPage(ctx, { markup, filters, load, render, summary, debounce })
 * Renders `markup` (page + toolbar() + resultsPanel()/resultsList()), wires the toolbar and fills
 * #results with render(items) and #count with summary(items). Errors go to the #alert region.
 * `filters` is a module-level object so filters survive navigation. Returns <main> or null if stale.
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
 * editPage(ctx, { markup, formId, save, message, redirect })
 * Renders a form view, saves through save(data), flashes `message` and goes to redirect(saved).
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
 * bindToggle(main, { confirm, run, success, refresh })
 * Wires the [data-action="toggle"] button: confirm modal -> run() -> flash success(result) -> refresh().
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
