/** @module modules/info/controller — rutas informativas: guía de diseño, guía de demostración y diagrama de funciones; pantallas de error del router. */
import { toast } from '/js/core/ui.js';
import * as session from '/js/core/session.js';
import { onAction } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Ruta de la guía de diseño: permite probar temas de apariencia y restablecerlos.
 * @param {object} params - parámetros de ruta (sin uso).
 * @param {{render: Function}} ctx - contexto del router.
 * @returns {Promise<void>}
 */
async function design(params, ctx) {
  const main = ctx.render(view.design());
  if (!main) return;
  const done = () => toast('Apariencia actualizada.');
  onAction(main, {
    theme: (button) => { model.applyTheme(model.THEMES[Number(button.dataset.index)][1]); done(); },
    reset: () => { model.resetTheme(); done(); },
  });
}

/**
 * Ruta de la guía de demostración: carga la FAQ y muestra los accesos según los permisos.
 * @param {object} params - parámetros de ruta (sin uso).
 * @param {{render: Function}} ctx - contexto del router.
 * @returns {Promise<void>}
 */
async function guide(params, ctx) {
  ctx.render(view.guide(model.DEMO_ACCOUNTS, await model.faq(), session.can));
}

/**
 * Pinta "no encontrado"; main.js lo usa para rutas desconocidas y acciones fallidas.
 * @param {{render: Function}} ctx - contexto del router.
 * @param {string} [message] - descripción opcional.
 * @returns {*} resultado de `ctx.render`.
 */
export const notFound = (ctx, message) => ctx.render(view.notFound(message));
/**
 * Pinta "acceso restringido"; main.js lo usa para rutas con permiso denegado.
 * @param {{render: Function}} ctx - contexto del router.
 * @returns {*} resultado de `ctx.render`.
 */
export const restricted = (ctx) => ctx.render(view.restricted());

/**
 * Rutas del módulo.
 * - `#/diseno` (permiso `diseno`): guía de diseño.
 * - `#/guia` (permiso `guia`): guía de demostración.
 * - `#/funciones` (permiso `funciones`): diagrama de funciones.
 * @type {Array<{path: string, perm: string, section: string, action: Function}>}
 */
export const routes = [
  { path: 'diseno', perm: 'diseno', section: 'diseno', action: design },
  { path: 'guia', perm: 'guia', section: 'guia', action: guide },
  { path: 'funciones', perm: 'funciones', section: 'funciones', action: (p, ctx) => ctx.render(view.functions()) },
];
