import { html } from '/js/core/ui.js';

/** meter({ value, max, label, text }) -> accessible progress bar (presupuesto usado, cupo de libros...). */
export const meter = ({ value, max, label, text = '' }) => html`
  <div class="meter-block"><div class="meter-head"><span>${label}</span><span class="mono muted">${text}</span></div>
    <progress class="meter" value="${Math.min(Number(value) || 0, Number(max) || 0)}" max="${Number(max) || 1}" aria-label="${label}"></progress></div>`;
