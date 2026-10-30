/** @module components/toolbar — barra de búsqueda y filtros, con enlace de eventos. */
import { html, attrs, $, $$, debounce as debounced } from '/js/core/ui.js';
import { options } from './form.js';

/**
 * Barra de búsqueda y filtros. Los ids de los campos son iguales a sus nombres.
 * @param {Object} opts - Opciones.
 * @param {string} [opts.id] - Id del contenedor.
 * @param {Object} [opts.search] - Campo de búsqueda.
 * @param {string} opts.search.name - Nombre e id del campo.
 * @param {string} opts.search.label - Etiqueta.
 * @param {string} [opts.search.placeholder] - Placeholder.
 * @param {string} [opts.search.value] - Valor inicial.
 * @param {Array<Object>} [opts.filters] - Filtros tipo select.
 * @param {string} opts.filters[].name - Nombre e id.
 * @param {string} opts.filters[].label - Etiqueta.
 * @param {Array<Array<string>>} opts.filters[].options - Pares `[valor, etiqueta]`.
 * @param {string} [opts.filters[].value] - Valor seleccionado.
 * @param {boolean} [opts.filters[].grow] - El campo crece para ocupar espacio libre.
 * @param {string} [opts.submit] - Si se da, etiqueta del botón y renderiza un <form>; si no, un contenedor role=search.
 * @returns {Safe} HTML de la barra.
 * @example
 * toolbar({ search: { name: 'q', label: 'Buscar', value: f.q },
 *   filters: [{ name: 'estado', label: 'Estado', value: f.estado, options: [['', 'Todos'], ...labelItems('prestamo')] }] })
 */
export function toolbar({ id, search, filters = [], submit = '' }) {
  const fields = html`
    ${search ? html`<div class="field grow"><label for="${search.name}">${search.label}</label>
      <input id="${search.name}" name="${search.name}" type="search" value="${search.value ?? ''}"${attrs({ placeholder: search.placeholder })}></div>` : ''}
    ${filters.map((f) => html`<div class="field ${f.grow ? 'grow' : ''}"><label for="${f.name}">${f.label}</label>
      <select id="${f.name}" name="${f.name}">${options(f.options, f.value)}</select></div>`)}`;
  return submit
    ? html`<form class="toolbar" role="search" data-toolbar${attrs({ id })}>${fields}<button class="btn primary" type="submit">${submit}</button></form>`
    : html`<div class="toolbar" role="search" data-toolbar${attrs({ id })}>${fields}</div>`;
}

/**
 * Enlaza la toolbar: llama a onChange(valores) al cambiar un filtro o (con debounce) al teclear.
 * `state` (opcional) se actualiza en sitio para que los filtros sobrevivan a la navegación. Al enviar el
 * formulario se llama a onSubmit (por defecto onChange).
 * @param {HTMLElement} root - Elemento `[data-toolbar]`.
 * @param {function(Object): any} onChange - Recibe una copia de los valores `{nombre: valor}`.
 * @param {Object} [opts] - Opciones.
 * @param {number} [opts.debounce=250] - Retardo (ms) al teclear en búsquedas.
 * @param {Object} [opts.state] - Objeto compartido que se mantiene sincronizado con los valores.
 * @param {function(Object): any} [opts.onSubmit] - Manejador del envío del formulario.
 * @returns {function(): Object} Función que lee y devuelve el estado actual.
 * @example bindToolbar($('[data-toolbar]', main), (values) => recargar(values), { state: filtros });
 */
export function bindToolbar(root, onChange, { debounce = 250, state = {}, onSubmit } = {}) {
  const controls = $$('input[name], select[name]', root);
  const read = () => {
    for (const c of controls) state[c.name] = c.value;
    return state;
  };
  const fire = (fn) => () => fn?.({ ...read() });
  const typing = debounced(fire(onChange), debounce);
  for (const c of controls) {
    if (c.type === 'search') c.addEventListener('input', typing);
    else c.addEventListener('change', fire(onChange));
  }
  if (root.tagName === 'FORM') {
    root.addEventListener('submit', (event) => {
      event.preventDefault();
      fire(onSubmit || onChange)();
    });
  }
  return read;
}
