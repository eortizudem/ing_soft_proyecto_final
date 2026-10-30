/** @module modules/inicio/controller — ruta hash del tablero de inicio; orquesta modelo y vista */
import * as session from '/js/core/session.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Ruta `#inicio` (permiso `inicio`): carga estadísticas y dibuja el tablero.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto de render del router.
 * @returns {Promise<void>}
 */
async function show(params, ctx) {
  const stats = await model.stats(); // el servidor decide qué devuelve según el rol
  ctx.render(view.dashboard(session.get(), stats, session.can));
}

/** Rutas del módulo (hash path `inicio`, permiso `inicio`). */
export const routes = [{ path: 'inicio', perm: 'inicio', section: 'inicio', action: show }];
