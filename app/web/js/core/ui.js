// Low-level UI primitives: safe HTML templating, DOM shortcuts, debounce, messages and toast.
// Everything visual (buttons, forms, tables...) lives in /js/components/.

// ---- Safe HTML templating -------------------------------------------------
// html`...` escapes every interpolated value unless it is itself a Safe string
// (the result of another html`` call or raw()). Arrays are joined.
export class Safe extends String {}

const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ENTITIES[c]);

function part(value) {
  if (value instanceof Safe) return String(value);
  if (Array.isArray(value)) return value.map(part).join('');
  if (value === null || value === undefined || value === false) return '';
  return esc(value);
}

export const html = (strings, ...values) =>
  new Safe(strings.reduce((out, text, i) => out + text + (i < values.length ? part(values[i]) : ''), ''));
export const raw = (text) => new Safe(text);

// attrs({ min: 1, required: true, hidden: false }) -> ` min="1" required` (values escaped).
export const attrs = (map = {}) => raw(Object.entries(map)
  .filter(([, v]) => v !== undefined && v !== null && v !== false && v !== '')
  .map(([k, v]) => (v === true ? ` ${k}` : ` ${k}="${esc(v)}"`)).join(''));

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

export function debounce(fn, ms = 250) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

// ---- Messages: #flash (success after navigation), #alert (errors), toast ------
let flashMessage = '';
export const setFlash = (text) => { flashMessage = text; };
export function takeFlash() {
  const text = flashMessage;
  flashMessage = '';
  return text;
}

let toastTimer;
export function toast(text) {
  const box = $('#toast');
  clearTimeout(toastTimer);
  box.textContent = text;
  box.classList.add('show');
  toastTimer = setTimeout(() => { box.classList.remove('show'); box.textContent = ''; }, 4500);
}

/** Shows an error (string or thrown error) in #alert; `error.motivos` ([{mensaje}]) render as a list. */
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

export const clearError = () => {
  const box = $('#alert');
  if (box) box.textContent = '';
};
