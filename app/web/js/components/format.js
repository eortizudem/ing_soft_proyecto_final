// Display formatting (es-MX). Pure functions.
const LOCALE = 'es-MX';

/** money(1234.5) -> "$1,234.50" (MXN); money(1234.5, 'USD') -> "USD 1,234.50". */
export const money = (n, currency = 'MXN') =>
  Number(n || 0).toLocaleString(LOCALE, { style: 'currency', currency });
/** Purchase prices and budgets are USD (D-28). */
export const usd = (n) => money(n, 'USD');
export const number = (n) => Number(n || 0).toLocaleString(LOCALE);

/** Calendar date. YYYY-MM-DD strings are not shifted by the time zone. */
export function date(value) {
  if (!value) return '';
  const day = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (day) return new Date(+day[1], +day[2] - 1, +day[3]).toLocaleDateString(LOCALE);
  return new Date(value).toLocaleDateString(LOCALE);
}

/** Today as YYYY-MM-DD in local time (default/max of date inputs). */
export const today = () => new Date().toLocaleDateString('en-CA');

/** Date and time of a timestamp. */
export const datetime = (value) => (value ? new Date(value).toLocaleString(LOCALE) : '');

/** Physical location -> "Planta · Pasillo A · Librero 01 · Nivel 1". */
export const location = (u) =>
  u ? `${u.planta} · Pasillo ${u.pasillo} · Librero ${u.librero} · Nivel ${u.nivel}` : '';

/** User -> "A0512345 · María García"; book -> "LIB001 · Título". */
export const person = (u) => `${u.matricula} · ${u.nombre_completo}`;
export const book = (b) => `${b.clave} · ${b.titulo}`;

/** "3 resultado(s)" style counter; with `limit`, a full page adds a hint to narrow the search. */
export const count = (n, noun = 'resultado(s)', limit = 0) =>
  `${n} ${noun}` + (limit && n >= limit ? ` (primeros ${limit}: usa la búsqueda o los filtros para acotar)` : '');
