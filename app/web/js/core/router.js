// Hash router. Modules register { path: 'libros/:id', perm, roles (optional role names), section, action(params, ctx) }; ctx.query = parsed ?query.
import * as session from './session.js';

const routes = [];
let hooks = {};
let token = 0;

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

export const href = (path) => '#/' + path;

export function go(path) {
  const target = href(path);
  if (location.hash === target) dispatch();
  else location.hash = target;
}

const permitted = (route) => (!route.perm || [].concat(route.perm).some(session.can))
  && (!route.roles || route.roles.includes(session.get()?.rol));

// hooks: { enter(route), render(html), notFound(ctx), restricted(ctx), error(err, ctx) }
export function init(h) {
  hooks = h;
  window.addEventListener('hashchange', dispatch);
}

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
