/** @module modules/perfiles/controller — ruta hash de perfiles y permisos; orquesta modelo y vista */
import * as session from '/js/core/session.js';
import * as layout from '/js/core/layout.js';
import { dispatch } from '/js/core/router.js';
import { $, $$, showError, clearError, toast } from '/js/core/ui.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Ruta `#perfiles` (permiso `perfiles`): muestra la matriz y guarda cada cambio de casilla al instante; recarga sesión y navegación porque los permisos propios pueden cambiar.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto de render del router.
 * @returns {Promise<void>}
 */
async function show(params, ctx) {
  let data = await model.matrix();
  const editable = session.can('perfiles');
  const main = ctx.render(view.show(data, editable));
  if (!main) return;
  const box = $('#matrix', main);

  box.addEventListener('change', async (event) => {
    const input = event.target;
    if (!input.dataset.rol) return;
    clearError();
    $$('input', box).forEach((i) => { i.disabled = true; }); // se redibuja con el estado real al terminar
    try {
      data = await model.setPermission(input.dataset.rol, input.dataset.permiso, input.checked);
      await session.load(); // own permissions may have changed
      layout.renderNav();
      toast('Permisos actualizados.');
      if (!session.can('perfiles')) return dispatch();
    } catch (err) {
      showError(err);
    }
    box.innerHTML = view.matrix(data, editable); // reflects the server state either way
  });
}

/** Rutas del módulo (hash path `perfiles`, permiso `perfiles`). */
export const routes = [{ path: 'perfiles', perm: 'perfiles', section: 'perfiles', action: show }];
