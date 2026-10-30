/**
 * @module core/ui — primitivas de UI de bajo nivel: plantillas HTML seguras, atajos DOM, debounce, mensajes y toast.
 * Todo lo visual (botones, formularios, tablas...) vive en /js/components/.
 */

// ---- Safe HTML templating -------------------------------------------------
// html`...` escapes every interpolated value unless it is itself a Safe string
// (the result of another html`` call or raw()). Arrays are joined.
/**
 * Cadena ya escapada/confiable: `html` no vuelve a escapar valores de esta clase.
 * @extends String
 */
export class Safe extends String {}

/** @type {Object<string,string>} Mapa de caracteres a entidades HTML. */
const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
/**
 * Escapa `& < > " '` para insertar texto en HTML.
 * @param {any} value - Valor (null/undefined dan cadena vacía).
 * @returns {string} Texto escapado.
 */
export const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ENTITIES[c]);

/**
 * Convierte un valor interpolado en HTML: Safe tal cual, arrays unidos, vacíos/false omitidos, el resto escapado.
 * @param {any} value - Valor interpolado.
 * @returns {string}
 */
function part(value) {
  if (value instanceof Safe) return String(value);
  if (Array.isArray(value)) return value.map(part).join('');
  if (value === null || value === undefined || value === false) return '';
  return esc(value);
}

/**
 * Tag de plantilla que escapa cada valor interpolado salvo que sea {@link Safe}; los arrays se unen.
 * @param {TemplateStringsArray} strings - Fragmentos literales.
 * @param {...any} values - Valores a interpolar.
 * @returns {Safe} HTML seguro.
 * @example html`<p>${nombre}</p>${items.map((i) => html`<li>${i}</li>`)}`
 */
export const html = (strings, ...values) =>
  new Safe(strings.reduce((out, text, i) => out + text + (i < values.length ? part(values[i]) : ''), ''));
/**
 * Marca un texto como HTML confiable (sin escapar). Usar solo con contenido propio.
 * @param {string} text - HTML.
 * @returns {Safe}
 */
export const raw = (text) => new Safe(text);

/**
 * Serializa atributos HTML omitiendo valores vacíos o false; `true` genera atributo booleano.
 * @param {Object<string,any>} [map] - Nombre/valor de atributos.
 * @returns {Safe} Cadena con espacio inicial, valores escapados.
 * @example attrs({ min: 1, required: true, hidden: false }) // ' min="1" required'
 */
export const attrs = (map = {}) => raw(Object.entries(map)
  .filter(([, v]) => v !== undefined && v !== null && v !== false && v !== '')
  .map(([k, v]) => (v === true ? ` ${k}` : ` ${k}="${esc(v)}"`)).join(''));

/**
 * Atajo de querySelector.
 * @param {string} selector - Selector CSS.
 * @param {ParentNode} [root] - Raíz de búsqueda (por defecto `document`).
 * @returns {?HTMLElement}
 */
export const $ = (selector, root = document) => root.querySelector(selector);
/**
 * Atajo de querySelectorAll que devuelve un array.
 * @param {string} selector - Selector CSS.
 * @param {ParentNode} [root] - Raíz de búsqueda (por defecto `document`).
 * @returns {HTMLElement[]}
 */
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

/**
 * Retrasa la ejecución de `fn` hasta que pasen `ms` sin nuevas llamadas.
 * @param {Function} fn - Función a retrasar.
 * @param {number} [ms=250] - Retardo en milisegundos.
 * @returns {Function} Versión con debounce de `fn`.
 */
export function debounce(fn, ms = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

// ---- Messages: #flash (success after navigation), #alert (errors), toast ------
/** @type {string} Mensaje flash pendiente de mostrarse tras la navegación. */
let flashMessage = '';
/**
 * Guarda un mensaje de éxito para mostrarlo en #flash tras la siguiente navegación.
 * @param {string} text - Mensaje.
 * @returns {void}
 */
export const setFlash = (text) => { flashMessage = text; };
/**
 * Devuelve y consume el mensaje flash pendiente.
 * @returns {string} Mensaje (vacío si no había).
 */
export function takeFlash() {
  const text = flashMessage;
  flashMessage = '';
  return text;
}

/** @type {number|undefined} Temporizador del toast activo. */
let toastTimer;
/**
 * Muestra un aviso temporal (4,5 s) en #toast.
 * @param {string} text - Mensaje.
 * @returns {void}
 */
export function toast(text) {
  const box = $('#toast');
  clearTimeout(toastTimer);
  box.textContent = text;
  box.classList.add('show');
  toastTimer = setTimeout(() => { box.classList.remove('show'); box.textContent = ''; }, 4500);
}

/**
 * Muestra un error (texto o error lanzado) en #alert, o como toast si no existe; `error.motivos`
 * (`[{mensaje}]`) se pinta como lista.
 * @param {string|Error} error - Mensaje o error (con `motivos` opcional).
 * @returns {void}
 */
export function showError(error) {
  const box = $('#alert');
  const text = typeof error === 'string' ? error : error?.message || '';
  if (!box) return toast(text);
  box.replaceChildren(text);
  if (Array.isArray(error?.motivos) && error.motivos.length) {
    const list = document.createElement('ul');
    for (const m of error.motivos) list.append(Object.assign(document.createElement('li'), { textContent: m.mensaje || m }));
    box.append(list);
  }
  box.focus();
}

/**
 * Vacía la región #alert.
 * @returns {void}
 */
export const clearError = () => {
  const box = $('#alert');
  if (box) box.textContent = '';
};
