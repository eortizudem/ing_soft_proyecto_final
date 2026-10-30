/** @module modules/usuarios/view — HTML puro del módulo de usuarios (datos -> componentes): listado, formulario, ficha, historial, actualización e importación */
import { html } from '/js/core/ui.js';
import { LIST_LIMIT } from '/js/core/api.js';
import { page, btn, toolbar, resultsPanel, actions, dataTable, statusBadge, formView, submitButton, detailView,
  labelItems, label, roleName, count, date, datetime, money, notice, book } from '/js/components/index.js';

/**
 * Página de listado de usuarios: búsqueda, filtros por perfil y estado, contenedor de resultados y accesos a actualizar/importar/crear.
 * @param {Array<{nombre: string, descripcion: string}>} roles - Perfiles para el filtro.
 * @param {{q: string, rol: string, estado: string}} filters - Valores actuales de los filtros.
 * @returns {*} Página (componente `page`).
 */
export const listPage = (roles, filters) => page({
  title: 'Gestión de usuarios',
  desc: 'Consulta, registra y administra las cuentas de la comunidad.',
  actions: html`${btn({ label: 'Actualizar lista', href: 'usuarios/actualizar' })}${btn({ label: 'Importar lista de alumnos', href: 'usuarios/importar' })}${btn({ label: 'Crear usuario', href: 'usuarios/nuevo', variant: 'primary' })}`,
  body: html`
  ${toolbar({
    search: { name: 'q', label: 'Buscar usuario', value: filters.q, placeholder: 'Nombre, matrícula o correo' },
    filters: [
      { name: 'rol', label: 'Perfil', value: filters.rol, options: [['', 'Todos los perfiles'], ...roles.map((r) => [r.nombre, r.descripcion])] },
      { name: 'estado', label: 'Estado', value: filters.estado, options: [['', 'Todos los estados'], ...labelItems('estadoUsuario')] },
    ],
  })}
  ${resultsPanel()}
  ${actions([html`<p class="muted">Selecciona “Ver” para consultar datos o dar de baja una cuenta.</p>`,
    btn({ label: 'Perfiles y permisos', href: 'perfiles', variant: 'link' })])}`,
});

/**
 * Texto de resumen del listado (total y activos).
 * @param {Object[]} users - Usuarios cargados (con `estado`).
 * @returns {string}
 */
export const summary = (users) =>
  count(users.length, undefined, LIST_LIMIT) + ` · ${users.filter((u) => u.estado === 'activo').length} activos`;

/**
 * Tabla de usuarios con clave, nombre, perfil, estado y acciones Ver/Editar.
 * @param {Object[]} users - Usuarios (matricula, nombre_completo, rol, estado, id_usuario).
 * @param {Object<string, string>} roles - Mapa nombre de rol -> descripción (ver `roleMap`).
 * @returns {*} Tabla (componente `dataTable`).
 */
export const rows = (users, roles) => dataTable({
  rows: users,
  empty: { text: 'Prueba otro nombre, matrícula o correo.' },
  columns: [
    { label: 'Clave', key: 'matricula' },
    { label: 'Nombre', key: 'nombre_completo' },
    { label: 'Perfil', render: (u) => roleName(roles, u.rol) },
    { label: 'Estado', render: (u) => statusBadge('estadoUsuario', u.estado) },
    { label: 'Acciones', render: (u) => html`<div class="row-actions">${btn({ label: 'Ver', href: 'usuarios/' + u.id_usuario })}${btn({ label: 'Editar', href: `usuarios/${u.id_usuario}/editar` })}</div>` },
  ],
});

/**
 * Formulario de alta/edición de usuario.
 * @param {Object} user - Datos actuales (nombre_completo, matricula, correo, rol, estado, fuente_validacion, id_usuario).
 * @param {Array<{nombre: string, descripcion: string}>} roles - Perfiles seleccionables.
 * @param {boolean} editing - true al editar (matrícula de solo lectura, contraseña opcional).
 * @returns {*} Página con el formulario `user-form`.
 */
export const form = (user, roles, editing) => page({
  title: editing ? 'Editar usuario' : 'Crear usuario',
  desc: 'Los campos marcados con * son obligatorios.',
  body: formView({
    id: 'user-form',
    footnote: 'Los datos de esta demostración son ficticios.',
    fields: [
      { name: 'nombre_completo', label: 'Nombre completo', value: user.nombre_completo, required: true, maxlength: 100 },
      { name: 'matricula', label: 'Matrícula / nómina', value: user.matricula, required: true, maxlength: 24, placeholder: 'Ej. A0513001', readonly: editing },
      { name: 'correo', label: 'Correo institucional', type: 'email', value: user.correo, required: true, maxlength: 150, placeholder: 'nombre@ducky.edu.mx' },
      { name: 'rol', label: 'Perfil', type: 'select', required: true, value: user.rol, options: roles.map((r) => [r.nombre, r.descripcion]) },
      { name: 'estado', label: 'Estado', type: 'select', value: user.estado, options: labelItems('estadoUsuario') },
      { name: 'fuente_validacion', label: 'Origen del registro', type: 'select', value: user.fuente_validacion, options: labelItems('fuente') },
      { name: 'password', label: 'Contraseña', type: 'password', required: !editing, minlength: 6, autocomplete: 'new-password',
        hint: editing ? 'Déjala vacía para conservar la actual.' : 'Mínimo 6 caracteres.' },
    ],
    actions: [btn({ label: 'Cancelar', href: editing ? 'usuarios/' + user.id_usuario : 'usuarios', variant: 'link' }),
      submitButton(editing ? 'Guardar cambios' : 'Crear cuenta')],
  }),
});

/**
 * Ficha de usuario con datos institucionales, acciones (editar, baja/reactivar) e historial.
 * @param {Object} u - Cuenta (nombre_completo, matricula, rol, correo, estado, fuente_validacion, registro_vigente, fecha_alta, fecha_baja, prestamos_activos, adeudos_pendientes, adeudos_pendientes_n, id_usuario).
 * @param {Object<string, string>} roles - Mapa nombre de rol -> descripción.
 * @param {{prestamos: Object[], renovaciones: Object[], adeudos: Object[], espera: Object[], bitacora: Object[]}} hist - Historial.
 * @returns {*} Página (componente `page`).
 */
export const detail = (u, roles, hist) => page({
  title: 'Ficha de usuario',
  desc: 'Datos institucionales y situación de la cuenta.',
  body: html`${detailView({
    title: u.nombre_completo,
    sub: `${u.matricula} · ${roleName(roles, u.rol)}`,
    items: [
      ['Correo institucional', u.correo],
      ['Estado de cuenta', `${label('estadoUsuario', u.estado)} · ${label('fuente', u.fuente_validacion)}`],
      ['Registro vigente', u.registro_vigente ? 'Sí' : 'No'],
      ['Fecha de alta', date(u.fecha_alta) || '—'],
      ['Fecha de baja', date(u.fecha_baja) || '—'],
      ['Préstamos activos', `${u.prestamos_activos} préstamo(s) activo(s)`],
      ['Adeudos pendientes', `${money(u.adeudos_pendientes)} · ${u.adeudos_pendientes_n} adeudo(s)`],
    ],
    actions: [
      btn({ label: 'Editar usuario', href: `usuarios/${u.id_usuario}/editar`, variant: 'primary' }),
      btn({ label: u.estado === 'activo' ? 'Dar de baja' : 'Reactivar cuenta', action: 'toggle', variant: 'danger' }),
      btn({ label: 'Volver a usuarios', href: 'usuarios', variant: 'link' }),
    ],
  })}${historial(hist)}`,
});

/**
 * Tarjeta con título que envuelve una tabla del historial.
 * @param {string} title - Título de la sección.
 * @param {*} table - Contenido (tabla).
 * @returns {*}
 */
const section = (title, table) => html`<section class="card stack"><h3>${title}</h3>${table}</section>`;
/** Celda de libro (clave y título); alias del componente `book`. */
const libroCell = book;

/** Historial de la cuenta (RF-04): préstamos, renovaciones, adeudos, lista de espera y actividad. */
/**
 * Historial de la cuenta (RF-04): préstamos, renovaciones, adeudos, lista de espera y actividad.
 * @param {{prestamos: Object[], renovaciones: Object[], adeudos: Object[], espera: Object[], bitacora: Object[]}} h - Historial devuelto por la API.
 * @returns {*} Secciones con una tabla por tipo.
 */
export const historial = (h) => html`<div class="stack" id="historial"><h2>Historial</h2>
  ${section('Préstamos', dataTable({ rows: h.prestamos, empty: { text: 'Sin préstamos registrados.' }, columns: [
    { label: 'Libro', render: (p) => libroCell(p.libro) },
    { label: 'Préstamo', render: (p) => date(p.fecha_prestamo) },
    { label: 'Vence', render: (p) => date(p.fecha_vencimiento) },
    { label: 'Devuelto', render: (p) => date(p.fecha_devolucion) || '—' },
    { label: 'Renovaciones', key: 'num_renovaciones', align: 'center' },
    { label: 'Estado', render: (p) => statusBadge('prestamo', p.estado) },
  ] }))}
  ${section('Renovaciones', dataTable({ rows: h.renovaciones, empty: { text: 'Sin renovaciones.' }, columns: [
    { label: 'Préstamo', render: (r) => '#' + r.id_prestamo },
    { label: 'Fecha', render: (r) => datetime(r.fecha) },
    { label: 'Nuevo vencimiento', render: (r) => date(r.nueva_fecha_vencimiento) },
  ] }))}
  ${section('Adeudos', dataTable({ rows: h.adeudos, empty: { text: 'Sin adeudos.' }, columns: [
    { label: 'Tipo', render: (a) => label('adeudoTipo', a.tipo) },
    { label: 'Monto', render: (a) => money(a.monto), align: 'right' },
    { label: 'Estado', render: (a) => statusBadge('adeudo', a.estado) },
    { label: 'Fecha de pago', render: (a) => date(a.fecha_pago) || '—' },
    { label: 'Préstamo', render: (a) => '#' + a.id_prestamo },
  ] }))}
  ${section('Lista de espera', dataTable({ rows: h.espera, empty: { text: 'Sin solicitudes de espera.' }, columns: [
    { label: 'Libro', render: (w) => libroCell(w.libro) },
    { label: 'Posición', key: 'posicion', align: 'center' },
    { label: 'Estado', render: (w) => statusBadge('listaEspera', w.estado) },
  ] }))}
  ${section('Actividad reciente', dataTable({ rows: h.bitacora, empty: { text: 'Sin actividad registrada.' }, columns: [
    { label: 'Fecha', render: (b) => datetime(b.fecha) },
    { label: 'Acción', key: 'accion' },
    { label: 'Detalle', key: 'detalle' },
  ] }))}</div>`;

// --- Actualización desde Servicios Escolares y lista de alumnos CSV (D-23) ---
/**
 * Insignia de la acción de sincronización de un registro.
 * @param {string} a - 'nuevo' | 'cambio' | 'baja' | 'sin_cambios' | 'omitido'.
 * @returns {*}
 */
const accionBadge = (a) => statusBadge('accionSync', a);

/**
 * Vista previa de la actualización desde Servicios Escolares (D-23); el botón aplicar se deshabilita sin cambios pendientes.
 * @param {{registros: Object[], resumen: {nuevos: number, cambios: number, bajas: number}}} preview - Respuesta de GET /api/usuarios/actualizar.
 * @returns {*} Página con tabla de registros y contenedor `#resultado`.
 */
export const syncPage = (preview) => {
  const r = preview.resumen;
  const pending = r.nuevos + r.cambios + r.bajas;
  return page({
    title: 'Actualizar desde Servicios Escolares',
    desc: 'Vista previa de altas, modificaciones y bajas del lista de alumnos simulado antes de aplicarlas.',
    body: html`<section class="card stack"><p>${r.nuevos} alta(s) · ${r.cambios} modificación(es) · ${r.bajas} baja(s)</p>
      ${dataTable({ rows: preview.registros, empty: { text: 'El origen no tiene registros.' }, columns: [
        { label: 'Clave', key: 'matricula' },
        { label: 'Nombre', key: 'nombre_completo' },
        { label: 'Perfil', render: (x) => x.rol || '' },
        { label: 'Acción', render: (x) => accionBadge(x.accion) },
        { label: 'Detalle', render: (x) => x.motivo || (x.cambios && x.cambios.length ? 'Cambia: ' + x.cambios.join(', ') : '') },
      ] })}</section>
      <div id="resultado"></div>
      ${actions([
        btn({ label: 'Aplicar actualización', action: 'aplicar', variant: 'primary', disabled: pending === 0 }),
        btn({ label: 'Volver a usuarios', href: 'usuarios', variant: 'link' }),
      ])}`,
  });
};

/**
 * Tabla de credenciales iniciales (se muestran una sola vez); vacío si no hay.
 * @param {Array<{matricula: string, password: string}>} list - Credenciales generadas.
 * @returns {*}
 */
const credentials = (list) => list.length ? html`<h3>Credenciales iniciales (se muestran una sola vez)</h3>
  ${dataTable({ rows: list, columns: [{ label: 'Clave', key: 'matricula' }, { label: 'Contraseña', key: 'password' }] })}` : '';

/**
 * Resultado de aplicar la actualización: aviso, omitidos y credenciales.
 * @param {{creados: number, actualizados: number, bajas: number, omitidos: Array<{matricula: string, motivo: string}>, credenciales_iniciales: Object[]}} r - Respuesta de POST /api/usuarios/actualizar.
 * @returns {*}
 */
export const syncResult = (r) => html`${notice({ tone: 'success',
  text: `Actualización aplicada: ${r.creados} alta(s), ${r.actualizados} modificación(es), ${r.bajas} baja(s).` })}
  ${r.omitidos.length ? html`<h3>Omitidos</h3>${dataTable({ rows: r.omitidos, columns: [
    { label: 'Clave', key: 'matricula' }, { label: 'Motivo', key: 'motivo' }] })}` : ''}
  ${credentials(r.credenciales_iniciales)}`;

/**
 * Página de importación de lista de alumnos por CSV (archivo y área de texto).
 * @returns {*} Página con el formulario `import-form` y contenedor `#resultado`.
 */
export const importPage = () => page({
  title: 'Importar lista de alumnos (CSV)',
  desc: 'Altas y modificaciones de alumnos y docentes desde Servicios Escolares.',
  body: html`${formView({
    id: 'import-form',
    footnote: 'Columnas: matricula, nombre_completo, correo, rol, estado (alumno o docente; el estado es opcional).',
    fields: [
      { name: 'archivo', label: 'Archivo CSV', type: 'file', accept: '.csv,text/csv', span: 'full' },
      { name: 'csv', label: 'Contenido CSV', type: 'textarea', required: true, span: 'full',
        placeholder: 'matricula,nombre_completo,correo,rol,estado' },
    ],
    actions: [submitButton('Importar'), btn({ label: 'Volver a usuarios', href: 'usuarios', variant: 'link' })],
  })}<div id="resultado"></div>`,
});

/**
 * Resultado de la importación: aviso, errores por línea y credenciales.
 * @param {{creados: number, actualizados: number, errores: Array<{linea: number, motivo: string}>, credenciales_iniciales: Object[]}} r - Respuesta de POST /api/usuarios/importar.
 * @returns {*}
 */
export const importResult = (r) => html`${notice({ tone: 'success',
  text: `Importación terminada: ${r.creados} alta(s), ${r.actualizados} modificación(es), ${r.errores.length} error(es).` })}
  ${r.errores.length ? html`<h3>Errores por línea</h3>${dataTable({ rows: r.errores, columns: [
    { label: 'Línea', key: 'linea' }, { label: 'Motivo', key: 'motivo' }] })}` : ''}
  ${credentials(r.credenciales_iniciales)}`;
