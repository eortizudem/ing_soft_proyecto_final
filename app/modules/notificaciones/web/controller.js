import { listPage } from '/js/core/crud.js';
import * as model from './model.js';
import * as view from './view.js';

const filters = { q: '', canal: '', periodo: '' };
const filtersMine = { q: '', canal: '', periodo: '' };

const list = (params, ctx) => listPage(ctx, {
  markup: view.listPage(filters),
  filters,
  load: model.list,
  render: (items) => view.rows(items),
  summary: view.summary,
});

const mine = (params, ctx) => listPage(ctx, {
  markup: view.listPage(filtersMine, true),
  filters: filtersMine,
  load: model.mine,
  render: (items) => view.rows(items, true),
  summary: view.summary,
});

export const routes = [
  { path: 'notificaciones', perm: 'notificaciones', section: 'notificaciones', action: list },
  { path: 'notificaciones/mias', section: 'notificaciones', action: mine },
];
