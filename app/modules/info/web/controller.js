import { toast } from '/js/core/ui.js';
import * as session from '/js/core/session.js';
import { onAction } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

async function design(params, ctx) {
  const main = ctx.render(view.design());
  if (!main) return;
  const done = () => toast('Apariencia actualizada.');
  onAction(main, {
    theme: (button) => { model.applyTheme(model.THEMES[Number(button.dataset.index)][1]); done(); },
    reset: () => { model.resetTheme(); done(); },
  });
}

async function guide(params, ctx) {
  ctx.render(view.guide(model.DEMO_ACCOUNTS, await model.faq(), session.can));
}

// Used by main.js for unknown routes, denied routes and failed actions.
export const notFound = (ctx, message) => ctx.render(view.notFound(message));
export const restricted = (ctx) => ctx.render(view.restricted());

export const routes = [
  { path: 'diseno', perm: 'diseno', section: 'diseno', action: design },
  { path: 'guia', perm: 'guia', section: 'guia', action: guide },
  { path: 'funciones', perm: 'funciones', section: 'funciones', action: (p, ctx) => ctx.render(view.functions()) },
];
