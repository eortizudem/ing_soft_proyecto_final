import { html, attrs, $, $$, debounce as debounced } from '/js/core/ui.js';
import { options } from './form.js';

/**
 * toolbar({ id, search, filters, submit })
 *  search:  { name, label, placeholder, value }
 *  filters: [{ name, label, options:[[value,label]], value, grow }]
 *  submit:  label -> renders a <form> with a submit button; otherwise a plain role=search container.
 * Field ids equal their names.
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
 * bindToolbar(root, onChange, { debounce, state, onSubmit })
 * Calls onChange(values) when a filter changes or (debounced) while typing. `state` (optional) is
 * updated in place so filters survive navigation. Submitting calls onSubmit (default onChange).
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
