/**
 * @module core/router — router por hash. Los módulos registran `{ path: 'libros/:id', perm, roles (nombres de rol, opcional), section, action(params, ctx) }`;
 * `ctx.query` contiene la query `?...` ya parseada.
 */
import * as session from './session.js';

/** @type {Array<Object>} Rutas registradas, con `keys` (nombres de parámetros) y `re` (regex compilada). */
const routes = [];
/** @type {Object} Hooks del host registrados en `init`. */
let hooks = {};
/** @type {number} Contador de navegación; invalida renders de despachos obsoletos. */
let token = 0;

/**
 * Registra rutas; las literales tienen prioridad sobre las parametrizadas.
 * @param {Array<Object>} list - Rutas del módulo.
 * @param {string} list[].path - Patrón, p. ej. 'libros/:id'.
 * @param {string|string[]} [list[].perm] - Permiso(s) requerido(s) (basta uno).
 * @param {string[]} [list[].roles] - Roles permitidos.
 * @param {string} [list[].section] - Sección de navegación activa.
 * @param {function(Object, Object): any} list[].action - Manejador `(params, ctx)`.
 * @returns {void}
 */
export function register(list) {
  for (const route of list) {
    const keys = [...route.path.matchAll(/:(\w+)/g)].map((m) => m[1]);
    const re = new RegExp('^' + route.path.replace(/:\w+/g, '([^/]+)') + '$');
    routes.push({ ...route, keys, re });
  }
  // Literal paths win over parametrised ones ('movil/asistente' before 'movil/:id'); stable otherwise.
  routes.sort((a, b) => a.keys.length - b.keys.length);
}

/** True when some module registered a route matching `path` (menu entries hide missing modules). */
export const hasRoute = (path) => routes.some((r) => r.re.test(path));

/**
 * Convierte una ruta en su enlace hash.
 * @param {string} path - Ruta sin `#/`.
 * @returns {string} `'#/' + path`.
 */
export const href = (path) => '#/' + path;

/**
 * Navega a una ruta; si ya está en ella fuerza un nuevo despacho.
 * @param {string} path - Ruta sin `#/`.
 * @returns {void}
 */
export function go(path) {
  const target = href(path);
  if (location.hash === target) dispatch();
  else location.hash = target;
}

/**
 * Indica si el usuario actual cumple el permiso y el rol exigidos por la ruta.
 * @param {Object} route - Ruta registrada.
 * @returns {boolean}
 */
const permitted = (route) => (!route.perm || [].concat(route.perm).some(session.can))
  && (!route.roles || route.roles.includes(session.get()?.rol));

/**
 * Inicializa el router y escucha `hashchange`.
 * @param {Object} h - Hooks del host.
 * @param {function(Object): void} h.enter - Se llama antes de cada acción con la ruta.
 * @param {function(string): HTMLElement} h.render - Pinta el HTML y devuelve el elemento de página.
 * @param {function(Object): any} h.notFound - Ruta inexistente.
 * @param {function(Object): any} h.restricted - Sin permiso.
 * @param {function(Error, Object): any} h.error - Error lanzado por una acción.
 * @returns {void}
 */
export function init(h) {
  hooks = h;
  window.addEventListener('hashchange', dispatch);
}

/**
 * Resuelve la ruta actual del hash y ejecuta su acción (requiere sesión). Construye `ctx` con
 * `params`, `query` y `render` (devuelve null si hay un despacho más reciente).
 * @returns {Promise<void>}
 */
export async function dispatch() {
  if (!session.get()) return;
  const mine = ++token;
  // "#/libros/nuevo?id_detalle=3": the path is matched without the query; handlers read it from ctx.query.
  const [rawPath, search = ''] = location.hash.replace(/^#\/?/, '').split('?');
  const path = decodeURIComponent(rawPath) || 'inicio';
  const ctx = {
    params: {},
    query: Object.fromEntries(new URLSearchParams(search)),
    render: (html) => (mine === token ? hooks.render(html) : null),
  };
  let route = null;
  for (const candidate of routes) {
    const match = candidate.re.exec(path);
    if (match) {
      route = candidate;
      candidate.keys.forEach((key, i) => { ctx.params[key] = match[i + 1]; });
      break;
    }
  }
  try {
    if (!route) {
      hooks.enter({ section: 'inicio' });
      await hooks.notFound(ctx);
    } else if (!permitted(route)) {
      hooks.enter({ section: 'inicio' });
      await hooks.restricted(ctx);
    } else {
      hooks.enter(route);
      await route.action(ctx.params, ctx);
    }
  } catch (err) {
    if (mine === token && session.get()) hooks.error(err, ctx);
  }
}
