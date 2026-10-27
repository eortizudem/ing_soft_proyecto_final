// App shell: sidebar (nav filtered by permisos), topbar with breadcrumb, main area.
import * as session from './session.js';
import { hasRoute } from './router.js';
import { $, html, takeFlash } from './ui.js';
import { brand, btn, badge } from '/js/components/index.js';

// [key, label, own]: key = permiso = ruta; `own` = ruta personal para quien inicia sesión sin ese permiso.
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
const EXTRA_TITLES = { guia: 'Guía de demostración', funciones: 'Funciones', restricted: 'Acceso restringido' };

let mode = '';
let section = 'inicio';
let handlers = {};

export function init(h) {
  handlers = h;
  // The skip link would change the hash and trigger the router: focus main instead.
  $('.skip').addEventListener('click', (event) => {
    event.preventDefault();
    $('#main')?.focus();
  });
}

// Forget the current layout (after login/logout) so the next enter() rebuilds it.
export const reset = () => { mode = ''; };

export function showLogin(markup) {
  mode = 'login';
  $('#app').innerHTML = markup;
}

function navHtml() {
  const entries = NAV.map(([key, name, own]) => {
    const path = session.can(key) ? key : (own && !session.isVisitor() ? own : '');
    return path && hasRoute(path) ? btn({ label: name, href: path, variant: section === key ? 'active' : '', current: section === key }) : '';
  });
  return html`${entries}`;
}

export function renderNav() {
  const nav = $('#main-nav');
  if (nav) nav.innerHTML = String(navHtml());
}

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

function bindShell() {
  $('#logout').addEventListener('click', () => handlers.onLogout());
  const menu = $('#menu');
  menu.addEventListener('click', () => {
    const open = $('#sidebar').classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
}

// Called by the router before each action. route: { section, bare }
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

// Renders a view into #main, shows any pending flash message, sets the document title from the
// page <h1> and returns the fresh .page element (safe to attach listeners to).
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
