// Login, visitor access and password recovery. Shown whenever there is no session.
import * as session from '/js/core/session.js';
import * as layout from '/js/core/layout.js';
import { $ } from '/js/core/ui.js';
import { bindForm, onAction } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

let onAuthenticated = () => {};

export function show(callback, state = {}) {
  onAuthenticated = callback;
  screen('login', state);
}

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

export async function logout() {
  try {
    await model.logout();
  } catch {
    /* session may already be gone */
  }
  session.clear();
}
