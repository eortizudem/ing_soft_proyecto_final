import { listPage, editPage } from '/js/core/crud.js';
import { setFlash } from '/js/core/ui.js';
import { confirmAction, onAction, count } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

const filters = { q: '', estado: '' };

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

async function list(params, ctx) {
  const refresh = () => list(params, ctx);
  const main = await listPage(ctx, {
    markup: view.listPage(filters), filters, load: model.list, render: view.rows, summary: view.summary,
  });
  if (main) bindCancel(main, { refresh });
}

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

async function mine(params, ctx) {
  const refresh = () => mine(params, ctx);
  const main = await listPage(ctx, {
    markup: view.minePage(), load: model.mine, render: view.mineRows, summary: (items) => count(items.length),
  });
  if (main) bindCancel(main, { refresh });
}

export const routes = [
  { path: 'espera', perm: 'espera', section: 'espera', action: (params, ctx) => (ctx.query.matricula || ctx.query.id_libro ? add(params, ctx) : list(params, ctx)) },
  { path: 'espera/nueva', perm: 'espera', section: 'espera', action: add },
  { path: 'espera/mias', section: 'espera', action: mine },
  { path: 'espera/unirse/:id_libro', section: 'espera', action: join },
];
