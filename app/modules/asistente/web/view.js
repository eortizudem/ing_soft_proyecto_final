// Asistente views: pure markup built from shared components.
import { html, raw, esc } from '/js/core/ui.js';
import {
  page, brand, btn, chatPanel, chatBubble, formView, submitButton, toolbar, dataTable, statusBadge,
  resultsPanel, labelItems, datetime,
} from '/js/components/index.js';

const lines = (text) => raw(String(text ?? '').split('\n').map(esc).join('<br>'));

const bookList = (books = []) => html`<ul class="stack">${books.map((b) => html`<li>
  <a href="#/libros/${b.id_libro}/ubicacion"><strong>${b.titulo}</strong></a> (${b.clave}) · ${b.disponibles} disponibles · ${b.ubicacion}</li>`)}</ul>`;

const links = (items = []) => html`<p>${items.map((l) => btn({ label: l.texto, href: l.ruta, variant: 'link' }))}</p>`;

/** One bubble from a stored message ({emisor, texto}) or an API answer ({texto, libros, enlaces}). */
export const bubble = (m, emisor = m.emisor) => chatBubble({
  emisor, texto: lines(m.texto), extra: html`${m.libros?.length ? bookList(m.libros) : ''}${m.enlaces?.length ? links(m.enlaces) : ''}`,
});

export const welcome = () => bubble({ texto: '¡Hola! Soy el asistente de LibriGest. Pregúntame por horarios, reglas de préstamo, renovaciones, multas o busca un libro por título, autor o tema.' }, 'asistente');

const chips = (items) => html`<div class="actions" role="group" aria-label="Preguntas sugeridas">
  ${items.map((t) => btn({ label: t, action: 'chip', data: { texto: t } }))}</div>`;

const rateForm = () => formView({
  id: 'rate-form', grid: false, stars: false,
  fields: [{ name: 'calificacion', label: '¿Te ayudó esta conversación?', type: 'select', required: true,
    options: [['', 'Selecciona'], ['5', '5 · Excelente'], ['4', '4 · Buena'], ['3', '3 · Regular'], ['2', '2 · Mala'], ['1', '1 · Muy mala']] },
  { name: 'resuelta', label: 'Mi duda quedó resuelta', type: 'checkbox' }],
  actions: [submitButton('Enviar respuesta')],
});

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

export const consultasPage = (filters) => page({
  title: 'Consultas para el bibliotecario',
  desc: 'Conversaciones que pidieron atención de un bibliotecario.',
  actions: btn({ label: 'Volver al asistente', href: 'asistente', variant: 'link' }),
  body: html`${toolbar({ id: 'esc-filters', filters: [{ name: 'estado', label: 'Estado', value: filters.estado,
    options: [['', 'Todas'], ...labelItems('consulta')] }] })}${resultsPanel()}`,
});

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
