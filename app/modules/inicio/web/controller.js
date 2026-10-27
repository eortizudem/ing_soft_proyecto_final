import * as session from '/js/core/session.js';
import * as model from './model.js';
import * as view from './view.js';

async function show(params, ctx) {
  const stats = await model.stats(); // el servidor decide qué devuelve según el rol
  ctx.render(view.dashboard(session.get(), stats, session.can));
}

export const routes = [{ path: 'inicio', perm: 'inicio', section: 'inicio', action: show }];
