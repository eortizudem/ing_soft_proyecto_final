/** @module modules/info/view — vistas informativas: guía de diseño, guía de demostración, diagrama de funciones y pantallas de acceso restringido / no encontrado. */
import { html } from '/js/core/ui.js';
import { page, btn, actions, card, grid, linkCard, notice, dataTable, disclosure } from '/js/components/index.js';
import { THEMES, MODULES } from './model.js';

/**
 * Guía de diseño: explica colores, tipografía y logo, con botones de acción `theme` y `reset` para probar la apariencia.
 * @returns {object} página.
 */
export const design = () => page({
  title: 'Guía de diseño de LibriGest',
  desc: 'Colores, tipografía y logo compartidos. Prueba un cambio y abre otra sección para ver el resultado; la preferencia se guarda solo en este navegador.',
  body: html`
  ${[
    ['Colores', 'Primario: botones y marca. Fondo y Superficie: separación del contenido. Texto: lectura y jerarquía. Éxito, Aviso y Error: comunicación de estados.'],
    ['Tipografía', 'Títulos para pantallas y secciones; cuerpo para formularios y mensajes; tipografía monoespaciada para identificadores y datos.'],
    ['Logo', 'El logotipo original identifica el acceso y la navegación. Todas las pantallas utilizan el mismo archivo.'],
  ].map(([title, text]) => card({ title, body: html`<p class="muted">${text}</p>` }))}
  ${actions(THEMES.map(([name], n) => btn({ label: name, action: 'theme', data: { index: n } })))}
  ${actions([btn({ label: 'Restablecer apariencia', action: 'reset' }), btn({ label: 'Volver al inicio', href: 'inicio' })])}`,
});

/**
 * Guía de demostración: accesos a módulos permitidos, aviso, credenciales demo y preguntas frecuentes.
 * @param {Array<{rol: string, matricula: string, password: string, nota: string}>} accounts - cuentas de demostración.
 * @param {Array<{pregunta: string, respuesta: string, categoria: string}>} faq - preguntas frecuentes (se omite el bloque si está vacío).
 * @param {function(string): boolean} [can] - indica si el usuario tiene un permiso (filtra los módulos mostrados).
 * @returns {object} página.
 */
export const guide = (accounts, faq, can = () => true) => page({
  title: 'Guía de demostración',
  desc: 'Cuentas de prueba y preguntas frecuentes.',
  body: html`
  ${grid(MODULES.filter((m) => can(m.perm)).map((m) => linkCard({ title: m.title, text: m.text, href: m.href })))}
  ${notice({ text: 'Los datos de la aplicación se guardan en PostgreSQL. Las credenciales de demostración no son un sistema de seguridad de producción.' })}
  ${card({ body: disclosure('Credenciales de demostración', dataTable({
    columns: [{ label: 'Perfil', key: 'rol' }, { label: 'Cuenta', key: 'matricula' }, { label: 'Contraseña', key: 'password' }, { label: 'Escenario', key: 'nota' }],
    rows: accounts,
  })) })}
  ${faq.length ? card({ title: 'Preguntas frecuentes', cls: 'faq', body: faq.map((f) =>
    disclosure(f.pregunta, html`<p>${f.respuesta}</p><p class="tiny muted">${f.categoria}</p>`)) }) : ''}`,
});

/**
 * Lista con viñetas.
 * @param {string[]} items - elementos.
 * @returns {object} `<ul>`.
 */
const list = (items) => html`<ul>${items.map((i) => html`<li>${i}</li>`)}</ul>`;

/**
 * Diagrama general de funciones: una tarjeta por módulo con sus funciones y botón de acceso.
 * @returns {object} página.
 */
export const functions = () => page({
  title: 'Diagrama general de funciones',
  desc: 'Módulos y flujos del proyecto LibriGest.',
  body: grid(MODULES.map((m) => card({ title: m.title, body: html`${list(m.items)}${btn({ label: m.button, href: m.href })}` })),
    { cols: 3, cls: 'diagram-columns' }),
});

/**
 * Pantalla de acceso restringido (el perfil no tiene permiso).
 * @returns {object} página.
 */
export const restricted = () => page({
  title: 'Acceso restringido',
  desc: 'Tu perfil no tiene permisos para esta función.',
  body: actions([btn({ label: 'Volver al inicio', href: 'inicio' })]),
});

/**
 * Pantalla de registro no encontrado.
 * @param {string} [message] - descripción a mostrar; por defecto un texto genérico.
 * @returns {object} página.
 */
export const notFound = (message) => page({
  title: 'Registro no encontrado',
  desc: message || 'Es posible que la referencia ya no exista.',
  body: actions([btn({ label: 'Volver al inicio', href: 'inicio' })]),
});
