/** @module modules/auth/controller — login, acceso de visitante y recuperación de contraseña; se muestra siempre que no hay sesión. */
import * as session from '/js/core/session.js';
import * as layout from '/js/core/layout.js';
import { $ } from '/js/core/ui.js';
import { bindForm, onAction } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Callback que se invoca al iniciar sesión o entrar como visitante.
 * @type {function(): void}
 */
let onAuthenticated = () => {};

/**
 * Muestra la pantalla de acceso.
 * @param {function(): void} callback - se invoca cuando el usuario queda autenticado.
 * @param {{matricula?: string, notice?: string}} [state] - datos para la pantalla de login.
 * @returns {void}
 */
export function show(callback, state = {}) {
  onAuthenticated = callback;
  screen('login', state);
}

/**
 * Pinta una pantalla de acceso y enlaza sus acciones (volver, olvidé contraseña, visitante, demo) y formularios.
 * @param {'login'|'forgot'|'reset'} name - pantalla a mostrar.
 * @param {object} [data] - datos para la vista.
 * @returns {void}
 */
function screen(name, data = {}) {
  layout.showLogin(view[name](data));
  const main = $('#main');
  main.focus({ preventScroll: true });
  onAction(main, {
    back: () => screen('login'),
    forgot: () => screen('forgot'),
    visitor: async () => {
      session.set(await model.visitor());
      onAuthenticated();
    },
    demo: (button) => {
      $('#matricula').value = button.dataset.matricula;
      $('#password').value = button.dataset.password;
      $('#matricula').focus();
    },
  });

  if (name === 'login') {
    bindForm($('#login-form'), { onSubmit: async (d) => {
      session.set(await model.login(d.matricula, d.password));
      onAuthenticated();
    } });
  }
  if (name === 'forgot') {
    bindForm($('#forgot-form'), { onSubmit: async (d) => {
      const { token } = await model.requestReset(d.correo);
      screen('reset', { token: token || '', hasToken: !!token });
    } });
  }
  if (name === 'reset') {
    bindForm($('#reset-form'), { onSubmit: async (d) => {
      await model.confirmReset(d.token, d.password);
      screen('login', { notice: 'Contraseña actualizada. Ya puedes iniciar sesión.' });
    } });
  }
}

/**
 * Cierra la sesión en el servidor (ignora el error si ya expiró) y limpia la sesión local.
 * @returns {Promise<void>}
 */
export async function logout() {
  try {
    await model.logout();
  } catch {
    /* session may already be gone */
  }
  session.clear();
}
