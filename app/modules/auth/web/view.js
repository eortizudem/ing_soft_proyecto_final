/** @module modules/auth/view — pantallas de acceso (login, recuperar, nueva contraseña); HTML puro. */
import { html } from '/js/core/ui.js';
import { page, brand, btn, formView, formActions, submitButton, notice } from '/js/components/index.js';
import { DEMO_ACCOUNTS } from './model.js';

/**
 * Marco común de las pantallas de acceso: identidad institucional y contenedor `#main`.
 * @param {object} content - contenido de la pantalla.
 * @returns {object} HTML de la pantalla completa.
 */
function frame(content) {
  return html`<div class="login">
    <section class="identity">${brand()}<h1>Tu biblioteca,<br>más cerca.</h1>
      <p class="slogan">Encuentra conocimiento.<br>Organiza tu biblioteca.<br>Conecta con nuevas ideas.</p>
      <div class="university"><h2>Universidad Ducky</h2><p>Biblioteca · Catálogo · Comunidad</p></div></section>
    <main id="main" class="login-content" tabindex="-1"><div class="page">${content}</div></main></div>`;
}

/**
 * Formulario de acceso con botón de regreso y de envío.
 * @param {string} id - id del formulario.
 * @param {Array<object>} fields - definición de campos.
 * @param {object} back - botón izquierdo (volver u olvidé contraseña).
 * @param {string} submit - texto del botón de envío.
 * @returns {object} formulario.
 */
const authForm = (id, fields, back, submit) => formView({
  id, fields, card: false, grid: false, stars: false,
  actions: [back, submitButton(submit)],
});

/**
 * Pantalla de inicio de sesión: formulario, acceso como visitante y botones de cuentas demo.
 * @param {{matricula?: string, notice?: string}} [datos] - matrícula a precargar y mensaje de éxito opcional.
 * @returns {object} pantalla.
 */
export const login = ({ matricula = '', notice: message = '' } = {}) => frame(page({
  title: 'Bienvenido a LibriGest',
  desc: 'Accede con tu cuenta institucional.',
  body: html`
  ${notice({ text: message, tone: 'success' })}
  ${authForm('login-form', [
    { name: 'matricula', label: 'Matrícula o número de colaborador', value: matricula, required: true, autocomplete: 'username' },
    { name: 'password', label: 'Contraseña', type: 'password', required: true, autocomplete: 'current-password' },
  ], btn({ label: '¿Olvidaste tu contraseña?', action: 'forgot', variant: 'link' }), 'Iniciar sesión')}
  ${formActions(btn({ label: 'Consultar como visitante', action: 'visitor' }))}
  <section class="stack"><p class="eyebrow">Accesos de demostración</p>
    <div class="demo-buttons">${DEMO_ACCOUNTS.map((a) =>
      btn({ label: a.boton || a.rol, action: 'demo', data: { matricula: a.matricula, password: a.password } }))}</div>
    <p class="footnote tiny">Selecciona un perfil para completar las credenciales.</p></section>`,
}));

/**
 * Botón "Volver al inicio de sesión" (acción `back`).
 * @type {object}
 */
const back = btn({ label: 'Volver al inicio de sesión', action: 'back', variant: 'link' });

/**
 * Pantalla para solicitar la recuperación con el correo institucional.
 * @returns {object} pantalla.
 */
export const forgot = () => frame(page({
  title: 'Recuperar contraseña',
  desc: 'Escribe el correo institucional de tu cuenta.',
  body: authForm('forgot-form', [
    { name: 'correo', label: 'Correo institucional', type: 'email', required: true, autocomplete: 'email' },
  ], back, 'Enviar instrucciones'),
}));

/**
 * Pantalla para capturar el código y la nueva contraseña.
 * @param {{token?: string, hasToken?: boolean}} [datos] - código a mostrar y precargar (solo en modo demostración).
 * @returns {object} pantalla.
 */
export const reset = ({ token = '', hasToken = false } = {}) => frame(page({
  title: 'Nueva contraseña',
  desc: hasToken
    ? 'Modo demostración: no se envía correo. Usa este código para continuar.'
    : 'Si el correo existe, recibirás un código. Escríbelo abajo junto con tu nueva contraseña.',
  body: html`${hasToken ? notice({ text: token, cls: 'token-box' }) : ''}
  ${authForm('reset-form', [
    { name: 'token', label: 'Código de recuperación', value: token, required: true, autocomplete: 'one-time-code' },
    { name: 'password', label: 'Nueva contraseña', type: 'password', required: true, minlength: 6, autocomplete: 'new-password' },
  ], back, 'Cambiar contraseña')}`,
}));
