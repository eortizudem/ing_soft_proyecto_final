import { html, attrs, raw, $, $$, showError, clearError } from '/js/core/ui.js';
import { btn } from './actions.js';

/** options([[value,label]|value], current) -> <option> list. */
export function options(items, current) {
  return html`${items.map((item) => {
    const [value, text] = Array.isArray(item) ? item : [item, item];
    return html`<option value="${value}"${String(value) === String(current) ? raw(' selected') : ''}>${text}</option>`;
  })}`;
}

/**
 * formField({ type, name, id, label, value, options, required, hint, readonly, min, max, step,
 *             maxlength, minlength, placeholder, autocomplete, list, accept, span, stars })
 * type: text|email|number|password|search|date|file|select|textarea|checkbox. span:'wide' spans both columns.
 * type 'file' takes `accept` (e.g. '.csv,text/csv') and is not part of serializeForm (see bindFileToText).
 * Required fields get an asterisk in the label unless stars:false.
 */
export function formField(f) {
  const { type = 'text', name, id = name, label: text, value = '', required, hint, span = '', stars = true } = f;
  const hintId = hint ? `${id}-hint` : undefined;
  const common = {
    id, name, required, readonly: f.readonly, 'aria-describedby': hintId,
  };
  const extra = {
    min: f.min, max: f.max, step: f.step, maxlength: f.maxlength, minlength: f.minlength,
    placeholder: f.placeholder, autocomplete: f.autocomplete, list: f.list, accept: f.accept,
  };
  let control;
  if (type === 'select') {
    control = html`<select${attrs(common)}>${options(f.options || [], value)}</select>`;
  } else if (type === 'textarea') {
    control = html`<textarea${attrs({ ...common, ...extra })}>${value}</textarea>`;
  } else if (type === 'checkbox') {
    return html`<div class="field check ${span}"><label><input type="checkbox"${attrs({ ...common, checked: !!value })}> ${text}</label>
      ${hint ? html`<span class="hint" id="${hintId}">${hint}</span>` : ''}</div>`;
  } else if (type === 'file') {
    control = html`<input type="file"${attrs({ ...common, accept: f.accept })}>`;
  } else {
    control = html`<input type="${type}" value="${value}"${attrs({ ...common, ...extra })}>`;
  }
  return html`<div class="field ${span}"><label for="${id}">${text}${required && stars ? ' *' : ''}</label>${control}
    ${hint ? html`<span class="hint" id="${hintId}">${hint}</span>` : ''}</div>`;
}

/**
 * formView({ id, fields, actions, footnote, error, card, grid, stars, children })
 * fields: formField configs rendered in a two-column grid; actions: array of btn() (right aligned).
 * Use submitButton()/cancel link inside actions. children: extra markup after the grid (datalists...).
 */
export function formView({ id, fields, actions: buttons = [], footnote = '', error = '', card = true, grid = true, stars = true, children = '' }) {
  const rendered = fields.map((f) => formField({ stars, ...f }));
  return html`<form${attrs({ id })} class="${card ? 'card ' : ''}form" novalidate>
    ${error ? html`<div class="notice error" role="alert">${error}</div>` : ''}
    ${grid ? html`<div class="form-grid">${rendered}</div>` : rendered}
    ${children}${footnote ? html`<p class="footnote">${footnote}</p>` : ''}
    ${formActions(buttons)}</form>`;
}

/** Right-aligned action row for forms. */
export const formActions = (items) => html`<div class="form-actions">${items}</div>`;

export const submitButton = (label) => btn({ label, type: 'submit', variant: 'primary' });

/** Form values as an object; checkboxes become booleans and file inputs are left out. */
export function serializeForm(form) {
  const data = Object.fromEntries(new FormData(form));
  for (const input of $$('input[type="file"][name]', form)) delete data[input.name];
  for (const box of $$('input[type="checkbox"][name]', form)) data[box.name] = box.checked;
  return data;
}

/** Fills `textarea` with the text of the file picked in `fileInput` (CSV import screens). */
export function bindFileToText(fileInput, textarea) {
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (file) textarea.value = await file.text();
  });
}

function validate(form) {
  for (const el of $$('[aria-invalid]', form)) {
    el.removeAttribute('aria-invalid');
    $(`#${el.id}-error`, form)?.remove();
  }
  const invalid = $$('input:invalid, select:invalid, textarea:invalid', form);
  for (const el of invalid) {
    el.setAttribute('aria-invalid', 'true');
    const error = document.createElement('span');
    error.className = 'error-text';
    error.id = `${el.id}-error`;
    error.textContent = el.validationMessage;
    el.closest('.field')?.append(error);
    el.setAttribute('aria-describedby', [el.getAttribute('aria-describedby'), error.id].filter(Boolean).join(' '));
  }
  invalid[0]?.focus();
  return !invalid.length;
}

/**
 * bindForm(form, { onSubmit(data), serialize })
 * Validates (aria-invalid + message, focuses the first invalid field), disables the submit button
 * while saving and shows server errors in the page's role=alert region.
 */
export function bindForm(form, { onSubmit, serialize = serializeForm }) {
  form.noValidate = true;
  form.addEventListener('input', (event) => {
    const el = event.target;
    if (el.getAttribute?.('aria-invalid')) {
      el.removeAttribute('aria-invalid');
      $(`#${el.id}-error`, form)?.remove();
    }
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearError();
    if (!validate(form)) return;
    const submit = $('[type="submit"]', form);
    form.setAttribute('aria-busy', 'true');
    if (submit) submit.disabled = true;
    try {
      await onSubmit(serialize(form));
    } catch (err) {
      showError(err);
    } finally {
      form.removeAttribute('aria-busy');
      if (submit?.isConnected) submit.disabled = false;
    }
  });
}
