import * as session from '/js/core/session.js';
import { $, setFlash, showError } from '/js/core/ui.js';
import { listPage, editPage, bindToggle } from '/js/core/crud.js';
import { onAction, bindForm, bindFileToText, confirmAction, printHtml } from '/js/components/index.js';
import { downloadPdf } from '/js/core/pdf.js';
import * as model from './model.js';
import * as view from './view.js';

const filters = { q: '', campo: '', tema: '', estado: '', tipo_uso: '', disponibilidad: '' };

async function list(params, ctx) {
  const themes = await model.themes();
  await listPage(ctx, {
    markup: view.listPage(themes, filters),
    filters,
    load: model.list,
    render: view.rows,
    summary: view.summary,
  });
}

async function edit(params, ctx) {
  const editing = !!params.id;
  // "#/libros/nuevo?id_detalle=N": book received by Compras; prefill from the pending line.
  const idDetalle = editing ? '' : ctx.query.id_detalle || '';
  const [themes, book, pend] = await Promise.all([model.themes(), editing ? model.get(params.id) : model.emptyBook(),
    idDetalle ? model.pendientes().catch(() => []) : []]);
  const pending = pend.find((p) => String(p.id_detalle) === idDetalle) || null;
  if (pending) Object.assign(book, { titulo: pending.descripcion, ejemplares: pending.cantidad_recibida,
    precio_referencia: Number(pending.precio_unitario) || 0 });
  editPage(ctx, {
    markup: view.form(book, themes, editing, pending),
    formId: 'book-form',
    save: (data) => model.save(editing ? params.id : null, { ...data, id_detalle: pending ? idDetalle : '' }),
    message: 'Ficha bibliográfica guardada correctamente.',
    redirect: (saved) => 'libros/' + saved.id_libro,
  });
}

const canWait = () => !!session.get() && !session.isVisitor();

async function detail(params, ctx) {
  const book = await model.get(params.id);
  const canEdit = session.can('catalogo');
  const ejemplares = canEdit ? await model.ejemplares(book.id_libro) : null;
  const main = ctx.render(view.detail(book, { canEdit, canLocate: session.can('buscar'), canWait: canWait(), ejemplares }));
  if (!main || !canEdit) return;
  const refresh = () => detail(params, ctx);
  const etiqueta = () => model.etiqueta(book.id_libro);
  onAction(main, {
    baja: async (button) => {
      const { id, etiqueta: tag } = button.dataset;
      const select = $(`[data-motivo="${id}"]`, main);
      const motivo = select.value;
      select.removeAttribute('aria-invalid');
      if (!motivo) {
        select.setAttribute('aria-invalid', 'true');
        select.focus();
        return showError('Selecciona el motivo de baja del ejemplar.');
      }
      const ok = await confirmAction({ title: 'Dar de baja ejemplar', confirmLabel: 'Dar de baja',
        message: `¿Deseas dar de baja el ejemplar ${tag}? Quedará registrado el motivo.` });
      if (!ok) return;
      await model.baja(id, motivo);
      setFlash(`Ejemplar ${tag} dado de baja.`);
      await refresh();
    },
    reactivar: async (button) => {
      const { id, etiqueta: tag } = button.dataset;
      if (!(await confirmAction({ title: 'Reactivar ejemplar', confirmLabel: 'Reactivar', variant: 'primary',
        message: `¿Deseas reactivar el ejemplar ${tag}?` }))) return;
      await model.reactivar(id);
      setFlash(`Ejemplar ${tag} reactivado.`);
      await refresh();
    },
    imprimir: async () => printHtml(view.fichaBlock(await etiqueta())),
    pdf: async () => {
      const e = await etiqueta();
      downloadPdf(view.pdfLines(e), `ficha-${e.clave}.pdf`);
    },
  });
  const active = book.estado === 'activo';
  bindToggle(main, {
    confirm: () => ({
      title: active ? 'Confirmar baja de libro' : 'Reactivar libro',
      message: `¿Deseas ${active ? 'dar de baja' : 'reactivar'} «${book.titulo}»? La ficha permanecerá en el catálogo administrativo.`,
      confirmLabel: active ? 'Dar de baja' : 'Reactivar',
    }),
    run: () => model.toggle(book.id_libro),
    success: () => 'Estado del libro actualizado.',
    refresh,
  });
}

async function pendientes(params, ctx) {
  await listPage(ctx, { markup: view.pendientesPage(), load: model.pendientes, render: view.pendientesRows });
}

function importar(params, ctx) {
  const main = ctx.render(view.importPage());
  if (!main) return;
  bindFileToText($('#archivo', main), $('#csv', main));
  bindForm($('#import-form', main), {
    onSubmit: async (data) => {
      $('#import-result', main).innerHTML = String(view.importResult(await model.importar(data.csv)));
    },
  });
}

// ---- Public search (buscar), mobile mode and floor plan ----
const searchFilters = { q: '', campo: '', tema: '', tipo_uso: '', disponibilidad: '' };

async function search(params, ctx) {
  const mobile = ctx.mobile;
  const themes = mobile ? [] : await model.themes();
  await listPage(ctx, {
    markup: mobile ? view.mobilePage(searchFilters, session.can('asistente')) : view.searchPage(themes, searchFilters, canWait()),
    filters: searchFilters,
    load: model.search,
    render: (books) => view.searchResults(books, canWait()),
  });
}

const locate = (mobile) => async (params, ctx) => {
  ctx.render(view.locationPage(await model.get(params.id), mobile));
};
const searchMobile = (params, ctx) => search(params, Object.assign(ctx, { mobile: true }));
export const routes = [
  { path: 'catalogo', perm: 'catalogo', section: 'catalogo', action: list },
  { path: 'libros/nuevo', perm: 'catalogo', section: 'catalogo', action: edit },
  { path: 'libros/pendientes', perm: 'catalogo', section: 'catalogo', action: pendientes },
  { path: 'libros/importar', perm: 'catalogo', section: 'catalogo', action: importar },
  { path: 'libros/:id', perm: ['catalogo', 'buscar'], section: 'catalogo', action: detail },
  { path: 'libros/:id/editar', perm: 'catalogo', section: 'catalogo', action: edit },
  { path: 'buscar', perm: 'buscar', section: 'buscar', action: search },
  { path: 'movil', perm: 'buscar', bare: true, action: searchMobile },
  { path: 'movil/:id', perm: 'buscar', bare: true, action: locate(true) },
  { path: 'libros/:id/ubicacion', perm: 'buscar', section: 'buscar', action: locate(false) },
];
