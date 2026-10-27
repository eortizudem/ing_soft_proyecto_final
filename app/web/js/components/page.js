import { html } from '/js/core/ui.js';
import { logoSrc } from '/js/core/theme.js';

/**
 * page({ title, desc, actions, body }) -> header + message regions (#alert errors, #flash success) + body.
 * The router wraps the result in <div class="page"> (see layout.setContent).
 */
export const page = ({ title, desc = '', actions = '', body = '' }) => html`
  <header class="page-header"><div class="page-title"><h1>${title}</h1>${desc ? html`<p class="page-desc">${desc}</p>` : ''}</div>${actions ? html`<div class="page-actions">${actions}</div>` : ''}</header>
  <div id="alert" role="alert" class="notice error" tabindex="-1"></div>
  <div id="flash" role="status" class="notice success"></div>
  ${body}`;

export const brand = () =>
  html`<div class="brand"><img src="${logoSrc()}" width="40" height="40" alt="Logo LibriGest"><span>LibriGest</span></div>`;
