/** @module core/layout — shell de la app: barra lateral (navegación filtrada por permisos), barra superior con migas y área principal. */
import * as session from './session.js';
import { hasRoute } from './router.js';
import { $, html, takeFlash } from './ui.js';
import { brand, btn, badge } from '/js/components/index.js';

/** @type {Array<Array<string>>} Entradas `[key, etiqueta, own]`: key = permiso = ruta; `own` = ruta personal para quien inicia sesión sin ese permiso. */
const NAV = [
  ['inicio', 'Inicio'],
  ['prestamos', 'Préstamos y devoluciones'],
  ['espera', 'Lista de espera', 'espera/mias'],
  ['adeudos', 'Multas y pagos'],
  ['usuarios', 'Usuarios'],
  ['perfiles', 'Perfiles y permisos'],
  ['catalogo', 'Catálogo'],
  ['compras', 'Compras'],
  ['reportes', 'Reportes'],
  ['notificaciones', 'Notificaciones', 'notificaciones/mias'],
  ['buscar', 'Buscar y localizar'],
  ['asistente', 'Asistente'],
  ['diseno', 'Diseño'],
];
/** @type {Object<string,string>} Títulos de migas para secciones fuera de NAV. */
const EXTRA_TITLES = { guia: 'Guía de demostración', funciones: 'Funciones', restricted: 'Acceso restringido' };

/** @type {string} Layout activo: '' (ninguno), 'login', 'shell' o 'bare'. */
let mode = '';
/** @type {string} Sección activa (resalta la navegación y las migas). */
let section = 'inicio';
/** @type {{onLogout?: Function}} Callbacks del host (main.js). */
let handlers = {};

/**
 * Registra los callbacks del host y enlaza el skip link (enfoca <main> en vez de cambiar el hash).
 * @param {Object} h - Callbacks.
 * @param {Function} h.onLogout - Se invoca al pulsar «Cerrar sesión».
 * @returns {void}
 */
export function init(h) {
  handlers = h;
  // The skip link would change the hash and trigger the router: focus main instead.
  $('.skip').addEventListener('click', (event) => {
    event.preventDefault();
    $('#main')?.focus();
  });
}

/**
 * Olvida el layout actual (tras login/logout) para que el próximo `enter()` lo reconstruya.
 * @returns {void}
 */
export const reset = () => { mode = ''; };

/**
 * Sustituye toda la app por el marcado de la pantalla de login.
 * @param {Safe|string} markup - HTML del login.
 * @returns {void}
 */
export function showLogin(markup) {
  mode = 'login';
  $('#app').innerHTML = markup;
}

/**
 * Genera los botones de navegación que el usuario puede ver y cuya ruta existe.
 * @returns {Safe} HTML de la navegación.
 */
function navHtml() {
  const entries = NAV.map(([key, name, own]) => {
    const path = session.can(key) ? key : (own && !session.isVisitor() ? own : '');
    return path && hasRoute(path) ? btn({ label: name, href: path, variant: section === key ? 'active' : '', current: section === key }) : '';
  });
  return html`${entries}`;
}

/**
 * Repinta la navegación lateral (p. ej. tras cambiar permisos).
 * @returns {void}
 */
export function renderNav() {
  const nav = $('#main-nav');
  if (nav) nav.innerHTML = String(navHtml());
}

/**
 * Marcado del shell completo: sidebar, topbar, contenido y pie.
 * @returns {Safe} HTML del shell.
 */
function shell() {
  const user = session.get();
  return html`
    <aside class="sidebar" id="sidebar" aria-label="Navegación principal">
      ${brand()}<div class="library">BIBLIOTECA DUCKY</div>
      <nav id="main-nav">${navHtml()}</nav>
      <div class="sidebar-bottom">
        <p>Universidad Ducky</p><p class="mono">${user.rol_descripcion}</p>
        ${btn({ label: session.isVisitor() ? 'Iniciar sesión' : 'Cerrar sesión', id: 'logout' })}
      </div>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <button type="button" class="btn menu-toggle" id="menu" aria-label="Abrir o cerrar navegación" aria-expanded="false">☰</button>
        <p id="crumb">Biblioteca / Inicio</p>${badge(user.nombre_completo)}
      </header>
      <main id="main" tabindex="-1" class="content"></main>
      <footer class="page-footer"><p>LibriGest · Universidad Ducky</p>
        ${btn({ label: 'Guía de demostración', href: 'guia', when: session.can('guia') })}</footer>
    </div>`;
}

/** Enlaza los eventos del shell: cerrar sesión y abrir/cerrar el menú móvil. */
function bindShell() {
  $('#logout').addEventListener('click', () => handlers.onLogout());
  const menu = $('#menu');
  menu.addEventListener('click', () => {
    const open = $('#sidebar').classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
}

/**
 * Prepara el layout antes de cada acción del router: construye el shell o el marco móvil si cambió
 * el modo y actualiza la sección activa y las migas.
 * @param {Object} route - Ruta resuelta.
 * @param {string} [route.section] - Sección de navegación (por defecto 'inicio').
 * @param {boolean} [route.bare] - Si es true usa el marco móvil sin sidebar.
 * @returns {void}
 */
export function enter(route) {
  const wanted = route.bare ? 'bare' : 'shell';
  if (mode !== wanted) {
    $('#app').innerHTML = wanted === 'bare'
      ? '<main id="main" class="mobile-frame" tabindex="-1"></main>'
      : String(shell());
    mode = wanted;
    if (wanted === 'shell') bindShell();
  }
  if (wanted === 'shell') {
    section = route.section || 'inicio';
    renderNav();
    const name = (NAV.find(([key]) => key === section) || [])[1] || EXTRA_TITLES[section] || 'Inicio';
    $('#crumb').textContent = 'Biblioteca / ' + name;
    $('#sidebar').classList.remove('open');
    $('#menu').setAttribute('aria-expanded', 'false');
  }
}

/**
 * Pinta una vista en #main, muestra el mensaje flash pendiente, fija el título del documento a partir
 * del <h1> y devuelve el elemento .page recién creado (seguro para añadir listeners).
 * @param {Safe|string} markup - HTML de la vista.
 * @returns {HTMLElement} Elemento `.page`.
 */
export function setContent(markup) {
  const main = $('#main');
  main.innerHTML = `<div class="page">${markup}</div>`;
  const pageEl = main.firstElementChild;
  const flash = takeFlash();
  const box = $('#flash', pageEl);
  if (flash && box) box.textContent = flash;
  const title = $('h1', pageEl)?.textContent;
  document.title = title ? `${title} · LibriGest` : 'LibriGest · Universidad Ducky';
  main.focus({ preventScroll: true });
  window.scrollTo({ top: 0 });
  return pageEl;
}
