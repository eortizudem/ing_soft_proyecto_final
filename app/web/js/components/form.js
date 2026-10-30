/** @module components/form — campos, vista de formulario, validación y envío (`bindForm`) compartidos. */
import { html, attrs, raw, $, $$, showError, clearError } from '/js/core/ui.js';
import { btn } from './actions.js';

/**
 * Lista de `<option>`; marca como seleccionada la que coincide con `current`.
 * @param {Array<Array<any>|any>} items - Pares `[valor, etiqueta]` o valores simples (valor = etiqueta).
 * @param {any} [current] - Valor seleccionado (se compara como texto).
 * @returns {Safe} HTML de las opciones.
 * @example options([['', 'Todos'], ['activo', 'Activo']], 'activo')
 */
export function options(items, current) {
  return html`${items.map((item) => {
    const [value, text] = Array.isArray(item) ? item : [item, item];
    return html`<option value="${value}"${String(value) === String(current) ? raw(' selected') : ''}>${text}</option>`;
  })}`;
}

/**
 * Campo de formulario (etiqueta + control + pista). Los campos obligatorios llevan asterisco en la
 * etiqueta salvo que `stars` sea false. El tipo 'file' no entra en `serializeForm` (ver `bindFileToText`).
 * @param {Object} f - Configuración del campo.
 * @param {string} [f.type='text'] - text|email|number|password|search|date|file|select|textarea|checkbox.
 * @param {string} f.name - Atributo name.
 * @param {string} [f.id] - Atributo id (por defecto igual a `name`).
 * @param {string} f.label - Texto de la etiqueta.
 * @param {any} [f.value] - Valor inicial (en checkbox, estado marcado).
 * @param {Array<Array<any>|any>} [f.options] - Opciones de un select (ver `options`).
 * @param {boolean} [f.required] - Campo obligatorio.
 * @param {string} [f.hint] - Texto de ayuda enlazado con aria-describedby.
 * @param {boolean} [f.readonly] - Solo lectura.
 * @param {number|string} [f.min] - Mínimo.
 * @param {number|string} [f.max] - Máximo.
 * @param {number|string} [f.step] - Paso.
 * @param {number} [f.maxlength] - Longitud máxima.
 * @param {number} [f.minlength] - Longitud mínima.
 * @param {string} [f.placeholder] - Placeholder.
 * @param {string} [f.autocomplete] - Valor de autocomplete.
 * @param {string} [f.list] - Id de un datalist.
 * @param {string} [f.accept] - Tipos aceptados en 'file' (p. ej. '.csv,text/csv').
 * @param {string} [f.span] - 'wide' ocupa las dos columnas.
 * @param {boolean} [f.stars=true] - Mostrar asterisco en campos obligatorios.
 * @returns {Safe} HTML del campo.
 * @example formField({ name: 'titulo', label: 'Título', required: true, maxlength: 200 })
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
 * Formulario completo: campos en rejilla de dos columnas, aviso de error, nota y barra de acciones.
 * Se enlaza con `bindForm`.
 * @param {Object} opts - Opciones.
 * @param {string} opts.id - Id del <form>.
 * @param {Array<Object>} opts.fields - Configuraciones de `formField`.
 * @param {Array<Safe|string>} [opts.actions] - Botones alineados a la derecha (`submitButton()`, enlace de cancelar).
 * @param {string} [opts.footnote] - Nota al pie del formulario.
 * @param {string} [opts.error] - Mensaje de error inicial (aviso `role="alert"`).
 * @param {boolean} [opts.card=true] - Envolver en estilo de tarjeta.
 * @param {boolean} [opts.grid=true] - Disponer los campos en rejilla.
 * @param {boolean} [opts.stars=true] - Asterisco en campos obligatorios (heredado por cada campo).
 * @param {Safe|string} [opts.children] - Marcado extra tras la rejilla (datalists...).
 * @returns {Safe} HTML del formulario.
 * @example
 * formView({ id: 'libro-form', fields: [{ name: 'titulo', label: 'Título', required: true }],
 *   actions: [backLink('libros', 'Cancelar'), submitButton('Guardar')] })
 */
export function formView({ id, fields, actions: buttons = [], footnote = '', error = '', card = true, grid = true, stars = true, children = '' }) {
  const rendered = fields.map((f) => formField({ stars, ...f }));
  return html`<form${attrs({ id })} class="${card ? 'card ' : ''}form" novalidate>
    ${error ? html`<div class="notice error" role="alert">${error}</div>` : ''}
    ${grid ? html`<div class="form-grid">${rendered}</div>` : rendered}
    ${children}${footnote ? html`<p class="footnote">${footnote}</p>` : ''}
    ${formActions(buttons)}</form>`;
}

/**
 * Fila de acciones de formulario alineada a la derecha.
 * @param {Array<Safe|string>} items - Botones.
 * @returns {Safe} HTML de la fila.
 */
export const formActions = (items) => html`<div class="form-actions">${items}</div>`;

/**
 * Botón principal de envío.
 * @param {string} label - Texto.
 * @returns {Safe} HTML del botón.
 */
export const submitButton = (label) => btn({ label, type: 'submit', variant: 'primary' });

/**
 * Valores del formulario como objeto; las casillas pasan a booleanos y los campos de archivo se omiten.
 * @param {HTMLFormElement} form - Formulario.
 * @returns {Object<string,any>} Datos serializados.
 */
export function serializeForm(form) {
  const data = Object.fromEntries(new FormData(form));
  for (const input of $$('input[type="file"][name]', form)) delete data[input.name];
  for (const box of $$('input[type="checkbox"][name]', form)) data[box.name] = box.checked;
  return data;
}

/**
 * Rellena `textarea` con el texto del archivo elegido en `fileInput` (pantallas de importación CSV).
 * @param {HTMLInputElement} fileInput - Campo de archivo.
 * @param {HTMLTextAreaElement} textarea - Destino del texto.
 * @returns {void}
 */
export function bindFileToText(fileInput, textarea) {
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (file) textarea.value = await file.text();
  });
}

/**
 * Validación nativa con aria-invalid y mensaje visible por campo; enfoca el primer inválido.
 * @param {HTMLFormElement} form - Formulario.
 * @returns {boolean} true si todos los campos son válidos.
 */
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
 * Enlaza el envío del formulario: valida (aria-invalid + mensaje, enfoca el primer campo inválido),
 * deshabilita el botón mientras guarda y muestra los errores del servidor en la región role=alert.
 * @param {HTMLFormElement} form - Formulario (de `formView`).
 * @param {Object} opts - Opciones.
 * @param {function(Object): Promise<any>} opts.onSubmit - Recibe los datos serializados; si lanza, se muestra el error.
 * @param {function(HTMLFormElement): Object} [opts.serialize=serializeForm] - Serializador personalizado.
 * @returns {void}
 * @example bindForm($('#libro-form'), { onSubmit: async (data) => { await api.post('/libros', data); go('libros'); } });
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
