import { html } from '/js/core/ui.js';

/** notice({ text, tone:'info'|'success'|'error', role, cls }) -> .notice (nothing if no text) */
export const notice = ({ text, tone = 'info', role, cls = '' }) =>
  text ? html`<div class="notice ${tone === 'info' ? '' : tone} ${cls}" role="${role || (tone === 'error' ? 'alert' : 'status')}">${text}</div>` : '';
