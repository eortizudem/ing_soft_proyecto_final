// Bootstrap: load the session, register every module's routes, start the router.
import * as session from '/js/core/session.js';
import * as router from '/js/core/router.js';
import * as layout from '/js/core/layout.js';
import { onUnauthorized } from '/js/core/api.js';
import { apply as applyTheme } from '/js/core/theme.js';
import { install as reportErrors } from '/js/core/errores.js';
import * as auth from '/m/auth/controller.js';
import * as info from '/m/info/controller.js';

// Feature modules are discovered at runtime: a missing or broken module is skipped (and logged),
// it never breaks the shell. auth and info are mandatory and imported statically above.
const MODULES = ['inicio', 'usuarios', 'perfiles', 'catalogo', 'compras', 'prestamos', 'espera', 'adeudos',
  'asistente', 'reportes', 'notificaciones'];

async function loadModules() {
  const loaded = await Promise.all(MODULES.map(async (name) => {
    try {
      const mod = await import(`/m/${name}/controller.js`);
      return Array.isArray(mod.routes) ? mod : null;
    } catch (err) {
      console.warn(`Módulo "${name}" no disponible:`, err.message);
      return null;
    }
  }));
  return loaded.filter(Boolean);
}

function showLogin() {
  layout.reset();
  auth.show(afterLogin);
}

function afterLogin() {
  layout.reset();
  const target = session.isVisitor() ? 'buscar' : 'inicio';
  if (location.hash === '#/' + target) router.dispatch();
  else location.hash = '#/' + target;
}

async function logout() {
  await auth.logout();
  history.replaceState(null, '', location.pathname);
  showLogin();
}

async function boot() {
  applyTheme();
  const modules = await loadModules();
  layout.init({ onLogout: logout });
  onUnauthorized(() => { session.clear(); showLogin(); });
  router.register([...modules, info].flatMap((m) => m.routes));
  router.init({
    enter: layout.enter,
    render: layout.setContent,
    notFound: (ctx) => info.notFound(ctx),
    restricted: (ctx) => info.restricted(ctx),
    error: (err, ctx) => (err.status === 403 ? info.restricted(ctx) : info.notFound(ctx, err.message)),
  });
  if (await session.load()) router.dispatch();
  else showLogin();
}

reportErrors();
boot();
