/** @module core/theme — preferencia de tema de la interfaz, guardada solo en localStorage. */
/** @type {string} Clave de localStorage. */
const KEY = 'librigest-theme';
/** @type {{primary: string, background: string, font: string, logo: string}} Tema por defecto. */
const DEFAULTS = { primary: '#1e68b8', background: '#f4f8fc', font: 'Roboto', logo: 'open' };

/**
 * Lee el tema guardado mezclado con los valores por defecto.
 * @returns {Object} Tema vigente.
 */
function read() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY)) };
  } catch {
    return { ...DEFAULTS };
  }
}

/** @type {Object} Tema en uso. */
let current = read();

/**
 * Ruta del logo según el tema.
 * @returns {string} URL del SVG ('logo.svg' o 'logo-stacked.svg').
 */
export const logoSrc = () => '/assets/' + (current.logo === 'stacked' ? 'logo-stacked.svg' : 'logo.svg');

/**
 * Aplica el tema al documento (variables CSS y logos de marca).
 * @returns {void}
 */
export function apply() {
  const style = document.documentElement.style;
  style.setProperty('--primary', current.primary);
  style.setProperty('--bg', current.background);
  style.setProperty('--font', `'${current.font}',Arial,sans-serif`);
  document.querySelectorAll('.brand img').forEach((img) => { img.src = logoSrc(); });
}

/** Persiste el tema en localStorage (si está disponible) y lo aplica. */
function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(current));
  } catch {
    /* storage unavailable: theme lasts for this page only */
  }
  apply();
}

/**
 * Modifica parcialmente el tema, lo guarda y lo aplica.
 * @param {Object} patch - Claves a cambiar.
 * @param {string} [patch.primary] - Color primario.
 * @param {string} [patch.background] - Color de fondo.
 * @param {string} [patch.font] - Familia tipográfica.
 * @param {string} [patch.logo] - 'open' o 'stacked'.
 * @returns {void}
 */
export function set(patch) {
  current = { ...current, ...patch };
  save();
}

/**
 * Restablece el tema por defecto y borra la preferencia guardada.
 * @returns {void}
 */
export function reset() {
  current = { ...DEFAULTS };
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  apply();
}
