import { html } from '/js/core/ui.js';
import { label, tone } from './labels.js';

/** badge(text, tone) tone: 'good' | 'warn' | 'bad' */
export const badge = (text, kind = 'good') => html`<span class="badge ${kind}">${text}</span>`;

/** statusBadge('solicitud', 'pendiente') -> label and tone from labels.js */
export const statusBadge = (kind, value) => badge(label(kind, value), tone(kind, value));
