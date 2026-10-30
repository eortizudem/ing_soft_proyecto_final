/** @module components/format — formato de presentación (es-MX). Funciones puras. */
/** @type {string} Configuración regional de los formatos. */
const LOCALE = 'es-MX';

/**
 * Formatea un importe como moneda.
 * @param {number|string} n - Importe (vacío cuenta como 0).
 * @param {string} [currency='MXN'] - Código ISO de moneda.
 * @returns {string} Texto formateado.
 * @example money(1234.5) // "$1,234.50"; money(1234.5, 'USD') // "USD 1,234.50"
 */
export const money = (n, currency = 'MXN') =>
  Number(n || 0).toLocaleString(LOCALE, { style: 'currency', currency });
/**
 * Formatea un importe en dólares (precios de compra y presupuestos son USD, D-28).
 * @param {number|string} n - Importe.
 * @returns {string} Texto formateado.
 */
export const usd = (n) => money(n, 'USD');
/**
 * Formatea un número con separadores de miles.
 * @param {number|string} n - Número (vacío cuenta como 0).
 * @returns {string} Texto formateado.
 */
export const number = (n) => Number(n || 0).toLocaleString(LOCALE);

/**
 * Fecha de calendario; las cadenas YYYY-MM-DD no se desplazan por la zona horaria.
 * @param {string|Date} value - Fecha ISO o marca de tiempo.
 * @returns {string} Fecha local, o cadena vacía si no hay valor.
 */
export function date(value) {
  if (!value) return '';
  const day = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (day) return new Date(+day[1], +day[2] - 1, +day[3]).toLocaleDateString(LOCALE);
  return new Date(value).toLocaleDateString(LOCALE);
}

/**
 * Fecha de hoy como YYYY-MM-DD en hora local (valor por defecto o máximo de inputs de fecha).
 * @returns {string} Fecha de hoy.
 */
export const today = () => new Date().toLocaleDateString('en-CA');

/**
 * Fecha y hora de una marca de tiempo.
 * @param {string|Date} value - Marca de tiempo.
 * @returns {string} Texto local, o cadena vacía si no hay valor.
 */
export const datetime = (value) => (value ? new Date(value).toLocaleString(LOCALE) : '');

/**
 * Ubicación física de un ejemplar.
 * @param {?Object} u - Ubicación con `planta`, `pasillo`, `librero` y `nivel`.
 * @returns {string} Ej. "Planta · Pasillo A · Librero 01 · Nivel 1", o vacío si no hay ubicación.
 */
export const location = (u) =>
  u ? `${u.planta} · Pasillo ${u.pasillo} · Librero ${u.librero} · Nivel ${u.nivel}` : '';

/**
 * Usuario en una línea.
 * @param {Object} u - Usuario con `matricula` y `nombre_completo`.
 * @returns {string} Ej. "A0512345 · María García".
 */
export const person = (u) => `${u.matricula} · ${u.nombre_completo}`;
/**
 * Libro en una línea.
 * @param {Object} b - Libro con `clave` y `titulo`.
 * @returns {string} Ej. "LIB001 · Título".
 */
export const book = (b) => `${b.clave} · ${b.titulo}`;

/**
 * Contador tipo «3 resultado(s)»; con `limit`, una página llena añade un aviso para acotar la búsqueda.
 * @param {number} n - Cantidad mostrada.
 * @param {string} [noun='resultado(s)'] - Sustantivo.
 * @param {number} [limit=0] - Tope del listado (0 = sin tope).
 * @returns {string} Texto del contador.
 */
export const count = (n, noun = 'resultado(s)', limit = 0) =>
  `${n} ${noun}` + (limit && n >= limit ? ` (primeros ${limit}: usa la búsqueda o los filtros para acotar)` : '');
