import { label, onAction, bindForm, bindFileToText } from '/js/components/index.js';
import { $ } from '/js/core/ui.js';
import { listPage, editPage, bindToggle } from '/js/core/crud.js';
import * as model from './model.js';
import * as view from './view.js';

const filters = { q: '', rol: '', estado: '' };

async function list(params, ctx) {
  const roles = await model.roles();
  const map = model.roleMap(roles);
  await listPage(ctx, {
    markup: view.listPage(roles, filters),
    filters,
    load: model.list,
    render: (users) => view.rows(users, map),
    summary: view.summary,
  });
}

async function edit(params, ctx) {
  const editing = !!params.id;
  const [roles, user] = await Promise.all([model.roles(), editing ? model.get(params.id) : model.emptyUser()]);
  editPage(ctx, {
    markup: view.form(user, roles, editing),
    formId: 'user-form',
    save: (data) => model.save(editing ? params.id : null, data),
    message: 'Cuenta guardada correctamente.',
    redirect: (saved) => 'usuarios/' + saved.id_usuario,
  });
}

async function detail(params, ctx) {
  const empty = { prestamos: [], renovaciones: [], adeudos: [], espera: [], bitacora: [] };
  const [roles, user, hist] = await Promise.all([model.roles(), model.get(params.id),
    model.historial(params.id).catch(() => empty)]);
  const main = ctx.render(view.detail(user, model.roleMap(roles), hist));
  if (!main) return;
  const active = user.estado === 'activo';
  bindToggle(main, {
    confirm: () => ({
      title: active ? 'Confirmar baja' : 'Reactivar cuenta',
      message: `La cuenta de ${user.nombre_completo} ${active ? 'dejará de estar activa.' : 'volverá a estar activa.'}`,
      confirmLabel: active ? 'Confirmar baja' : 'Reactivar',
    }),
    run: () => model.toggle(user.id_usuario),
    success: (updated) => `Cuenta actualizada: ${label('estadoUsuario', updated.estado)}.`,
    refresh: () => detail(params, ctx),
  });
}

async function sync(params, ctx, result = '') {
  const main = ctx.render(view.syncPage(await model.syncPreview()));
  if (!main) return;
  $('#resultado', main).innerHTML = result;
  onAction(main, {
    // Aplicar y volver a dibujar la vista previa (ya sin cambios pendientes) conservando el resultado.
    aplicar: async () => sync(params, ctx, String(view.syncResult(await model.syncApply()))),
  });
}

function importar(params, ctx) {
  const main = ctx.render(view.importPage());
  if (!main) return;
  bindFileToText($('#archivo', main), $('#csv', main));
  bindForm($('#import-form', main), {
    onSubmit: async (data) => {
      $('#resultado', main).innerHTML = String(view.importResult(await model.importCsv(data.csv)));
    },
  });
}

export const routes = [
  { path: 'usuarios', perm: 'usuarios', section: 'usuarios', action: list },
  { path: 'usuarios/nuevo', perm: 'usuarios', section: 'usuarios', action: edit },
  { path: 'usuarios/actualizar', perm: 'usuarios', section: 'usuarios', action: sync },
  { path: 'usuarios/importar', perm: 'usuarios', section: 'usuarios', action: importar },
  { path: 'usuarios/:id', perm: 'usuarios', section: 'usuarios', action: detail },
  { path: 'usuarios/:id/editar', perm: 'usuarios', section: 'usuarios', action: edit },
];
