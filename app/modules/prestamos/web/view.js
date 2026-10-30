/**
 * @module modules/prestamos/view — HTML de préstamos, recibo y políticas (funciones puras: datos -> componentes; capa view).
 */
import { html } from '/js/core/ui.js';
import { LIST_LIMIT } from '/js/core/api.js';
import { page, btn, toolbar, resultsPanel, dataTable, statusBadge, formView, submitButton, detailView, receiptBlock,
  notice, note, labelItems, label, roleName, money, date, datetime, location, count, person, book } from '/js/components/index.js';


// ---------------------------------------------------------------- lista
/**
 * Página del listado de préstamos con barra de búsqueda y filtro de estado.
 * @param {{q: string, estado: string}} filters - Filtros actuales.
 * @param {boolean} canPolicies - Si el usuario puede ver el enlace a políticas (permiso `perfiles`).
 * @returns {Safe} Página con panel de resultados vacío.
 */
export const listPage = (filters, canPolicies) => page({
  title: 'Préstamos y devoluciones',
  desc: 'Registra préstamos, renovaciones y devoluciones de la biblioteca.',
  actions: html`${btn({ label: 'Nuevo préstamo', href: 'prestamos/nuevo', variant: 'primary' })}${btn({ label: 'Políticas de préstamo', href: 'politicas', variant: 'link', when: canPolicies })}`,
  body: html`${toolbar({
    search: { name: 'q', label: 'Buscar préstamo', value: filters.q, placeholder: 'Matrícula, nombre, clave, título o folio' },
    filters: [{ name: 'estado', label: 'Estado', value: filters.estado, options: [['', 'Todos los estados'], ...labelItems('prestamo')] }],
  })}${resultsPanel()}`,
});

/**
 * Texto del contador del listado.
 * @param {Array<Object>} items - Préstamos cargados (con `estado`).
 * @returns {string} Total y número de vencidos.
 */
export const summary = (items) => count(items.length, undefined, LIST_LIMIT) + ` · ${items.filter((p) => p.estado === 'vencido').length} vencido(s)`;

/**
 * Tabla de préstamos con acciones Ver/Renovar/Devolver (las dos últimas solo si está abierto).
 * @param {Array<Object>} items - Préstamos con `folio`, `usuario`, `libro`, `numero_copia`, `fecha_vencimiento`, `estado`, `multa_estimada`, `fecha_devolucion`, `id_prestamo`.
 * @returns {Safe} Tabla HTML.
 */
export const rows = (items) => dataTable({
  rows: items,
  empty: { text: 'Prueba otra búsqueda o cambia el estado.' },
  columns: [
    { label: 'Folio', key: 'folio' },
    { label: 'Usuario', render: (p) => person(p.usuario) },
    { label: 'Libro', render: (p) => `${book(p.libro)} (copia ${p.numero_copia})` },
    { label: 'Vence', render: (p) => date(p.fecha_vencimiento) },
    { label: 'Estado', render: (p) => html`${statusBadge('prestamo', p.estado)}${p.multa_estimada ? ` ${money(p.multa_estimada)}` : ''}` },
    { label: 'Acciones', render: (p) => html`<div class="row-actions">${btn({ label: 'Ver', href: 'prestamos/' + p.id_prestamo })}
      ${btn({ label: 'Renovar', action: 'renovar', data: { id: p.id_prestamo }, when: !p.fecha_devolucion })}
      ${btn({ label: 'Devolver', action: 'devolver', data: { id: p.id_prestamo }, when: !p.fecha_devolucion })}</div>` },
  ],
});

// ---------------------------------------------------------------- nuevo
/**
 * Página del formulario de nuevo préstamo (matrícula, clave, canales del recibo) con zona de validación.
 * @returns {Safe} Página.
 */
export const form = () => page({
  title: 'Nuevo préstamo',
  desc: 'Escribe la matrícula y la clave del libro: se validan las reglas antes de confirmar.',
  body: formView({
    id: 'loan-form',
    fields: [
      { name: 'matricula', label: 'Matrícula / nómina', required: true, maxlength: 24, placeholder: 'Ej. A0512345', autocomplete: 'off' },
      { name: 'clave', label: 'Clave del libro', required: true, maxlength: 24, placeholder: 'Ej. LIB001', autocomplete: 'off' },
      { name: 'canal_email', label: 'Enviar recibo por correo', type: 'checkbox', value: true },
      { name: 'canal_whatsapp', label: 'Enviar recibo por WhatsApp', type: 'checkbox' },
    ],
    children: html`<div id="validacion" aria-live="polite"></div>`,
    actions: [btn({ label: 'Cancelar', href: 'prestamos', variant: 'link' }), submitButton('Confirmar préstamo')],
  }),
});

/**
 * Resultado de validar RN-01: motivos de rechazo (con enlace a lista de espera si no hay copias) o resumen de autorización.
 * @param {?Object} r - Respuesta de `model.validar` (`autorizado`, `motivos`, `usuario`, `libro`, `dias_prestamo`, `fecha_vencimiento_estimada`).
 * @param {{matricula: string, clave: string}} values - Valores escritos, usados en el enlace a espera.
 * @returns {Safe|string} Aviso HTML, o cadena vacía si no hay respuesta.
 */
export const validacion = (r, { matricula, clave }) => {
  if (!r) return '';
  const lista = html`<ul>${r.motivos.map((m) => html`<li>${m.mensaje}</li>`)}</ul>`;
  if (!r.autorizado) {
    const sinCopias = r.motivos.some((m) => m.codigo === 'LIBRO_NO_DISPONIBLE') && r.libro;
    return html`${notice({ text: lista, tone: 'error' })}
      ${sinCopias ? btn({ label: 'Añadir a lista de espera', variant: 'link', href: `espera?matricula=${encodeURIComponent(matricula)}&id_libro=${r.libro.id_libro}` }) : ''}`;
  }
  const { usuario: u, libro: l } = r;
  return notice({
    tone: 'success',
    text: `Autorizado: ${u.nombre_completo} (${roleName({}, u.rol)}, ${u.prestamos_activos} de ${u.max_libros} libros) recibirá “${l.titulo}” `
      + `(${l.disponibles} disponible(s)). Plazo ${r.dias_prestamo} días hábiles; vence el ${date(r.fecha_vencimiento_estimada)}.`,
  });
};

// ---------------------------------------------------------------- detalle y recibo
/**
 * Pares etiqueta/valor del recibo de préstamo.
 * @param {Object} r - Recibo (`usuario`, `libro`, fechas, `dias_prestamo`, `politica`, `notificaciones`).
 * @returns {Array<Array>} Lista de `[etiqueta, valor]`.
 */
const receiptItems = (r) => [
  ['Usuario', person(r.usuario)],
  ['Perfil', roleName({}, r.usuario.rol)],
  ['Libro', book(r.libro)],
  ['Copia', r.libro.numero_copia],
  ['Ubicación', location(r.libro.ubicacion)],
  ['Fecha de préstamo', date(r.fecha_prestamo)],
  ['Fecha de vencimiento', date(r.fecha_vencimiento)],
  ['Plazo', `${r.dias_prestamo} días hábiles`],
  ['Renovaciones permitidas', r.politica.max_renovaciones],
  ['Multa por día hábil de retraso', money(r.politica.multa_diaria)],
  ['Avisos enviados', r.notificaciones.map((n) => `${label('canal', n.canal)} (${datetime(n.fecha)})`).join(', ') || 'Ninguno'],
];

/**
 * Líneas de texto del recibo para el PDF.
 * @param {Object} r - Recibo (ver `receiptItems`).
 * @returns {Array<string>} Líneas del documento.
 */
export const receiptLines = (r) => [
  'BIBLIOTECA DUCKY - RECIBO DE PRESTAMO', r.folio, '',
  ...receiptItems(r).map(([k, v]) => `${k}: ${v}`), '',
  'Devuelve el libro en la fecha de vencimiento para evitar multas.',
];

/**
 * Página de detalle del préstamo con acciones y bloque de recibo.
 * @param {Object} p - Préstamo con renovaciones y adeudos (`folio`, `libro`, `usuario`, `estado`, fechas, `num_renovaciones`, `max_renovaciones`, `dias_retraso`, `multa_estimada`, `renovaciones`, `adeudos`).
 * @param {Object} r - Recibo del préstamo.
 * @param {boolean} [canAdeudos=false] - Si se muestran los botones de pérdida y daño (permiso `adeudos`).
 * @returns {Safe} Página.
 */
export const detail = (p, r, canAdeudos = false) => {
  const abierto = !p.fecha_devolucion;
  return page({
    title: `Préstamo ${p.folio}`,
    desc: 'Detalle del préstamo, acciones y recibo.',
    body: html`${detailView({
      title: p.libro.titulo,
      sub: `${person(p.usuario)} · ${roleName({}, p.usuario.rol)}`,
      badge: statusBadge('prestamo', p.estado),
      items: [
        ['Libro', `${book(p.libro)} (copia ${p.numero_copia})`],
        ['Fecha de préstamo', date(p.fecha_prestamo)],
        ['Vencimiento', date(p.fecha_vencimiento)],
        ['Devolución', datetime(p.fecha_devolucion) || '—'],
        ['Renovaciones', `${p.num_renovaciones} de ${p.max_renovaciones}`],
        ['Retraso', p.dias_retraso ? `${p.dias_retraso} día(s) hábil(es)${abierto ? ` · multa estimada ${money(p.multa_estimada)}` : ''}` : 'Sin retraso'],
        ['Historial de renovaciones', p.renovaciones.map((x) => `${date(x.fecha)} → ${date(x.nueva_fecha_vencimiento)}`).join('; ') || '—'],
        ['Adeudos', p.adeudos.map((a) => `${label('adeudoTipo', a.tipo)} ${money(a.monto)} (${label('adeudo', a.estado)})`).join('; ') || '—'],
      ],
      actions: [
        btn({ label: 'Renovar', action: 'renovar', data: { id: p.id_prestamo }, variant: 'primary', when: abierto }),
        btn({ label: 'Devolver', action: 'devolver', data: { id: p.id_prestamo }, variant: 'primary', when: abierto }),
        btn({ label: 'Reportar pérdida', href: 'adeudos/perdida/' + p.id_prestamo, variant: 'danger', when: abierto && canAdeudos }),
        btn({ label: 'Reportar daño', href: 'adeudos/danio/' + p.id_prestamo, variant: 'danger', when: abierto && canAdeudos }),
        btn({ label: 'Volver a préstamos', href: 'prestamos', variant: 'link' }),
      ],
    })}
    ${receiptBlock({ id: 'recibo', title: 'Recibo de préstamo', folio: r.folio, items: receiptItems(r),
      footer: note('Importante', 'Devuelve el libro en la fecha de vencimiento para evitar multas.') })}
    <div class="actions">${btn({ label: 'Imprimir recibo', action: 'imprimir' })}${btn({ label: 'Descargar PDF', action: 'pdf' })}
      ${btn({ label: 'Enviar por correo', action: 'enviar', data: { canal: 'email' } })}
      ${btn({ label: 'Enviar por WhatsApp', action: 'enviar', data: { canal: 'whatsapp' } })}</div>`,
  });
};

// ---------------------------------------------------------------- politicas
/**
 * Tabla de políticas de préstamo por perfil.
 * @param {Array<Object>} items - Políticas (`rol`, `dias_prestamo`, `max_libros`, `max_renovaciones`, `multa_diaria`, `activa`, `id_politica`).
 * @returns {Safe} Página.
 */
export const policiesPage = (items) => page({
  title: 'Políticas de préstamo',
  desc: 'Días hábiles de préstamo, límites y multa por perfil. Los préstamos ya creados conservan su política.',
  actions: btn({ label: 'Volver a préstamos', href: 'prestamos', variant: 'link' }),
  body: html`<section class="card">${dataTable({
    rows: items,
    empty: { text: 'No hay políticas registradas.' },
    columns: [
      { label: 'Perfil', render: (p) => roleName({}, p.rol) },
      { label: 'Días hábiles', key: 'dias_prestamo', align: 'right' },
      { label: 'Máx. libros', key: 'max_libros', align: 'right' },
      { label: 'Máx. renovaciones', key: 'max_renovaciones', align: 'right' },
      { label: 'Multa diaria', render: (p) => money(p.multa_diaria), align: 'right' },
      { label: 'Activa', render: (p) => (p.activa ? 'Sí' : 'No') },
      { label: 'Acciones', render: (p) => btn({ label: 'Editar', href: 'politicas/' + p.id_politica }) },
    ],
  })}</section>`,
});

/**
 * Formulario de edición de una política.
 * @param {Object} p - Política (`rol`, `dias_prestamo`, `max_libros`, `max_renovaciones`, `multa_diaria`).
 * @returns {Safe} Página.
 */
export const policyForm = (p) => page({
  title: `Política de ${roleName({}, p.rol)}`,
  desc: 'Los campos marcados con * son obligatorios.',
  body: formView({
    id: 'policy-form',
    fields: [
      { name: 'dias_prestamo', label: 'Días hábiles de préstamo', type: 'number', value: p.dias_prestamo, required: true, min: 1, max: 365, step: 1 },
      { name: 'max_libros', label: 'Máximo de libros simultáneos', type: 'number', value: p.max_libros, required: true, min: 1, max: 100, step: 1 },
      { name: 'max_renovaciones', label: 'Máximo de renovaciones', type: 'number', value: p.max_renovaciones, required: true, min: 1, max: 20, step: 1 },
      { name: 'multa_diaria', label: 'Multa por día hábil (MXN)', type: 'number', value: p.multa_diaria, required: true, min: 0, step: 0.01 },
    ],
    actions: [btn({ label: 'Cancelar', href: 'politicas', variant: 'link' }), submitButton('Guardar política')],
  }),
});
