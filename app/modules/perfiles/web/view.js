import { html, attrs } from '/js/core/ui.js';
import { page, card, dataTable, badge, btn, actions } from '/js/components/index.js';

// El administrador conserva usuarios y perfiles (regla del servidor): esas casillas se muestran fijas.
const locked = (r, p) => r.nombre === 'admin' && ['usuarios', 'perfiles'].includes(p.nombre);

// Permission matrix: rows = permissions, columns = roles. Editable cells are checkboxes.
export const matrix = (data, editable) => dataTable({
  cls: 'matrix',
  rows: data.permisos,
  columns: [
    { label: 'Función', render: (p) => p.descripcion },
    ...data.roles.map((r) => ({
      label: r.descripcion,
      align: 'center',
      render: (p) => {
        const on = !!data.matriz[r.nombre]?.[p.nombre];
        if (!editable) return on ? badge('Sí') : html`<span class="muted">No</span>`;
        return html`<input type="checkbox"${attrs({ 'data-rol': r.nombre, 'data-permiso': p.nombre,
          'aria-label': `${r.descripcion}: ${p.descripcion}`, checked: on, disabled: locked(r, p) })}>`;
      },
    })),
  ],
});

export const show = (data, editable) => page({
  title: 'Perfiles y permisos',
  desc: 'Cada perfil accede únicamente a las funciones que necesita.',
  body: html`
  ${card({ id: 'matrix', title: '', body: matrix(data, editable) })}
  <p class="muted">${editable
    ? 'Marca o desmarca una casilla para cambiar el permiso del perfil. Se guarda al instante.'
    : 'Solo lectura.'}</p>
  ${actions([btn({ label: 'Políticas de préstamo', href: 'politicas' }), btn({ label: 'Volver a usuarios', href: 'usuarios', variant: 'link' })])}`,
});
