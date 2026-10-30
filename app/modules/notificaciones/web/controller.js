/** @module modules/notificaciones/controller — rutas de notificaciones: lista del personal y "mis notificaciones". */
import { listPage } from '/js/core/crud.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Filtros de la lista del personal.
 * @type {{q: string, canal: string, periodo: string}}
 */
const filters = { q: '', canal: '', periodo: '' };
/**
 * Filtros de "mis notificaciones".
 * @type {{q: string, canal: string, periodo: string}}
 */
const filtersMine = { q: '', canal: '', periodo: '' };

/**
 * Ruta de la lista de avisos de todos los usuarios.
 * @param {object} params - parámetros de ruta (sin uso).
 * @param {object} ctx - contexto del router.
 * @returns {Promise<void>}
 */
const list = (params, ctx) => listPage(ctx, {
  markup: view.listPage(filters),
  filters,
  load: model.list,
  render: (items) => view.rows(items),
  summary: view.summary,
});

/**
 * Ruta de los avisos del usuario actual.
 * @param {object} params - parámetros de ruta (sin uso).
 * @param {object} ctx - contexto del router.
 * @returns {Promise<void>}
 */
const mine = (params, ctx) => listPage(ctx, {
  markup: view.listPage(filtersMine, true),
  filters: filtersMine,
  load: model.mine,
  render: (items) => view.rows(items, true),
  summary: view.summary,
});

/**
 * Rutas del módulo.
 * - `#/notificaciones` (permiso `notificaciones`): lista del personal.
 * - `#/notificaciones/mias` (sin permiso específico; requiere sesión): avisos propios.
 * @type {Array<{path: string, section: string, action: Function}>}
 */
export const routes = [
  { path: 'notificaciones', perm: 'notificaciones', section: 'notificaciones', action: list },
  { path: 'notificaciones/mias', section: 'notificaciones', action: mine },
];
