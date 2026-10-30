/** @module modules/perfiles/view — HTML puro de la matriz de permisos por perfil */
import { html, attrs } from '/js/core/ui.js';
import { page, card, dataTable, badge, btn, actions } from '/js/components/index.js';

// El administrador conserva usuarios y perfiles (regla del servidor): esas casillas se muestran fijas.
/**
 * Indica si una casilla es fija: el admin conserva `usuarios` y `perfiles` (regla del servidor).
 * @param {{nombre: string}} r - Perfil.
 * @param {{nombre: string}} p - Permiso.
 * @returns {boolean}
 */
const locked = (r, p) => r.nombre === 'admin' && ['usuarios', 'perfiles'].includes(p.nombre);

/**
 * Matriz de permisos: filas = permisos, columnas = perfiles. Editable: casillas con `data-rol`/`data-permiso`; solo lectura: Sí/No.
 * @param {{roles: Array<{nombre: string, descripcion: string}>, permisos: Array<{nombre: string, descripcion: string}>, matriz: Object<string, Object<string, boolean>>}} data - Respuesta de GET /api/roles.
 * @param {boolean} editable - true si el usuario tiene el permiso `perfiles`.
 * @returns {*} Tabla (componente `dataTable`).
 */
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

/**
 * Página "Perfiles y permisos" con la matriz dentro de `#matrix`.
 * @param {Object} data - Respuesta de GET /api/roles (ver `matrix`).
 * @param {boolean} editable - true si se puede editar.
 * @returns {*} Página (componente `page`).
 */
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
