/** @module modules/asistente/view — vistas del asistente: chat, lista de consultas y detalle para el bibliotecario (markup puro a partir de componentes). */
import { html, raw, esc } from '/js/core/ui.js';
import {
  page, brand, btn, chatPanel, chatBubble, formView, submitButton, toolbar, dataTable, statusBadge,
  resultsPanel, labelItems, datetime,
} from '/js/components/index.js';

/**
 * Convierte saltos de línea en `<br>` escapando el texto.
 * @param {string} text - texto plano multilínea.
 * @returns {object} HTML seguro (`raw`).
 */
const lines = (text) => raw(String(text ?? '').split('\n').map(esc).join('<br>'));

/**
 * Lista de libros encontrados por el asistente, con enlace a su ubicación.
 * @param {Array<{id_libro: number, titulo: string, clave: string, disponibles: number, ubicacion: string}>} [books] - libros.
 * @returns {object} `<ul>` de libros.
 */
const bookList = (books = []) => html`<ul class="stack">${books.map((b) => html`<li>
  <a href="#/libros/${b.id_libro}/ubicacion"><strong>${b.titulo}</strong></a> (${b.clave}) · ${b.disponibles} disponibles · ${b.ubicacion}</li>`)}</ul>`;

/**
 * Botones de enlace sugeridos en una respuesta.
 * @param {Array<{texto: string, ruta: string}>} [items] - enlaces (ruta hash sin `#/`).
 * @returns {object} párrafo con botones.
 */
const links = (items = []) => html`<p>${items.map((l) => btn({ label: l.texto, href: l.ruta, variant: 'link' }))}</p>`;

/**
 * Burbuja de chat a partir de un mensaje guardado ({emisor, texto}) o una respuesta de la API ({texto, libros, enlaces}).
 * @param {{emisor?: string, texto: string, libros?: Array<object>, enlaces?: Array<object>}} m - mensaje o respuesta.
 * @param {string} [emisor=m.emisor] - `usuario` o `asistente`.
 * @returns {object} burbuja renderizable.
 */
export const bubble = (m, emisor = m.emisor) => chatBubble({
  emisor, texto: lines(m.texto), extra: html`${m.libros?.length ? bookList(m.libros) : ''}${m.enlaces?.length ? links(m.enlaces) : ''}`,
});

/**
 * Burbuja de bienvenida del asistente cuando la conversación está vacía.
 * @returns {object} burbuja del asistente.
 */
export const welcome = () => bubble({ texto: '¡Hola! Soy el asistente de LibriGest. Pregúntame por horarios, reglas de préstamo, renovaciones, multas o busca un libro por título, autor o tema.' }, 'asistente');

/**
 * Botones de preguntas sugeridas (acción `chip`, con el texto en `data-texto`).
 * @param {string[]} items - preguntas sugeridas.
 * @returns {object} grupo de botones.
 */
const chips = (items) => html`<div class="actions" role="group" aria-label="Preguntas sugeridas">
  ${items.map((t) => btn({ label: t, action: 'chip', data: { texto: t } }))}</div>`;

/**
 * Formulario `#rate-form` para calificar la conversación (1-5) y marcar si quedó resuelta.
 * @returns {object} formulario.
 */
const rateForm = () => formView({
  id: 'rate-form', grid: false, stars: false,
  fields: [{ name: 'calificacion', label: '¿Te ayudó esta conversación?', type: 'select', required: true,
    options: [['', 'Selecciona'], ['5', '5 · Excelente'], ['4', '4 · Buena'], ['3', '3 · Regular'], ['2', '2 · Mala'], ['1', '1 · Muy mala']] },
  { name: 'resuelta', label: 'Mi duda quedó resuelta', type: 'checkbox' }],
  actions: [submitButton('Enviar respuesta')],
});

/**
 * Pantalla del chat del asistente (escritorio o móvil): sugerencias, panel de chat y formulario de opinión.
 * @param {{suggestions: string[], staff: boolean, mobile: boolean, messages: Array<{emisor: string, texto: string}>}} datos - sugerencias, si el usuario es personal (muestra acceso a consultas), versión móvil e historial.
 * @returns {object} página.
 */
export function chatPage({ suggestions, staff, mobile, messages }) {
  return html`${mobile ? brand() : ''}${page({
    title: 'Asistente virtual',
    desc: 'Resuelve dudas de la biblioteca. Si no puedo ayudarte, escribe "hablar con un bibliotecario".',
    actions: html`${btn({ label: 'Consultas para el bibliotecario', href: 'asistente/consultas', when: !!staff && !mobile })}
      ${btn({ label: mobile ? 'Búsqueda móvil' : 'Ver en móvil', href: mobile ? 'movil' : 'movil/asistente', variant: 'link' })}
      ${btn({ label: 'Volver a escritorio', href: 'asistente', variant: 'link', when: mobile })}`,
    body: html`${chips(suggestions)}${chatPanel({ id: 'chat', messages: messages.length ? messages.map((m) => bubble(m)) : [welcome()],
      placeholder: 'Escribe tu pregunta' })}${rateForm()}`,
  })}`;
}

/**
 * Pantalla de consultas para el bibliotecario: barra de filtro por estado y panel de resultados.
 * @param {{estado: string}} filters - filtro actual (`''`, `pendiente`, `resuelta`).
 * @returns {object} página.
 */
export const consultasPage = (filters) => page({
  title: 'Consultas para el bibliotecario',
  desc: 'Conversaciones que pidieron atención de un bibliotecario.',
  actions: btn({ label: 'Volver al asistente', href: 'asistente', variant: 'link' }),
  body: html`${toolbar({ id: 'esc-filters', filters: [{ name: 'estado', label: 'Estado', value: filters.estado,
    options: [['', 'Todas'], ...labelItems('consulta')] }] })}${resultsPanel()}`,
});

/**
 * Tabla de consultas escaladas; cada fila enlaza a su detalle.
 * @param {Array<{id_conversacion: number, usuario: object|null, fecha_inicio: string, ultimo_mensaje: string, resuelta: boolean}>} items - consultas.
 * @returns {object} tabla de datos.
 */
export const consultaRows = (items) => dataTable({
  rows: items,
  empty: { title: 'Sin consultas', text: 'No hay conversaciones con este estado.' },
  rowHref: (e) => `asistente/consultas/${e.id_conversacion}`,
  columns: [
    { label: 'Usuario', render: (e) => (e.usuario ? `${e.usuario.nombre_completo} (${e.usuario.matricula})` : 'Visitante') },
    { label: 'Inicio', render: (e) => datetime(e.fecha_inicio) },
    { label: 'Último mensaje', key: 'ultimo_mensaje' },
    { label: 'Estado', render: (e) => statusBadge('consulta', e.resuelta ? 'resuelta' : 'pendiente') },
  ],
});

/**
 * Detalle de una consulta: historial de la conversación y, si está pendiente, formulario `#resolve-form` para responder.
 * @param {{id_conversacion: number, resuelta: boolean, usuario: object|null, mensajes: Array<{emisor: string, texto: string}>}} c - conversación.
 * @returns {object} página.
 */
export const consultaDetail = (c) => page({
  title: `Consulta #${c.id_conversacion}`,
  desc: c.usuario ? `${c.usuario.nombre_completo} (${c.usuario.matricula})` : 'Visitante',
  actions: html`${statusBadge('consulta', c.resuelta ? 'resuelta' : 'pendiente')}${btn({ label: 'Volver', href: 'asistente/consultas', variant: 'link' })}`,
  body: html`<section class="card chat"><div class="chat-log" role="log" aria-label="Conversación" tabindex="0">${c.mensajes.map((m) => bubble(m))}</div></section>
    ${c.resuelta ? '' : formView({ id: 'resolve-form', grid: false, fields: [
    { name: 'respuesta', label: 'Respuesta al usuario', type: 'textarea', required: true, maxlength: 500, span: 'wide',
      hint: 'Se guarda en la conversación con el prefijo [Bibliotecario].' }],
    actions: [submitButton('Marcar como atendida')] })}`,
});
