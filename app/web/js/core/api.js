/**
 * @module core/api — cliente fetch mínimo (mismo origen, JSON de entrada y salida).
 * Los errores lanzados llevan `message`, `status`, `data` y los campos del payload (p. ej. `motivos`).
 */
/** @type {?Function} Callback invocado ante un 401 inesperado (sesión expirada). */
let unauthorizedHandler = null;

/** @type {string[]} Rutas que gestionan su propio 401 (contraseña incorrecta, aún sin sesión). */
const OWN_401 = ['/login', '/visitante', '/me', '/logout', '/recuperar', '/recuperar/confirmar'];

/**
 * Registra el callback que se ejecuta cuando una llamada devuelve 401 fuera de `OWN_401`.
 * @param {Function} fn - Función sin argumentos (normalmente limpia la sesión y muestra el login).
 * @returns {void}
 */
export function onUnauthorized(fn) {
  unauthorizedHandler = fn;
}

/**
 * Ejecuta una petición a `/api` + `path` y devuelve el JSON de la respuesta.
 * @param {string} method - Verbo HTTP.
 * @param {string} path - Ruta relativa a /api (puede incluir query).
 * @param {Object} [body] - Cuerpo JSON; si es `undefined` no se envía.
 * @returns {Promise<?Object>} Datos de la respuesta (`null` si el cuerpo está vacío).
 * @throws {Error} Con `status`, `data` y los campos del payload; sin conexión no lleva `status`.
 */
async function request(method, path, body) {
  const options = { method, credentials: 'same-origin', headers: {} };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch('/api' + path, options);
  } catch {
    throw new Error('No se pudo conectar con el servidor. Inténtalo de nuevo.');
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    /* empty or non-JSON body */
  }
  if (!response.ok) {
    if (response.status === 401 && !OWN_401.includes(path.split('?')[0])) unauthorizedHandler?.();
    // Keep the whole payload: 422 rules carry `motivos: [{codigo, mensaje}]` (and any extra field).
    const error = new Error(data?.error || `Error del servidor (${response.status}).`);
    error.status = response.status;
    error.data = data;
    if (data && typeof data === 'object') Object.assign(error, { ...data, error: undefined });
    throw error;
  }
  return data;
}

/** @type {number} Tope de filas de los listados administrativos grandes (usuarios, préstamos, multas); se envía como `limite`. */
export const LIST_LIMIT = 500;

/**
 * Construye una query string omitiendo valores vacíos, nulos o indefinidos.
 * @param {Object} [params] - Pares nombre/valor.
 * @returns {string} `"?a=1&b=2"` o cadena vacía si no hay parámetros.
 * @example query({ q: 'dune', estado: '' }) // '?q=dune'
 */
export function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== '' && value !== null && value !== undefined) search.set(key, value);
  }
  const text = search.toString();
  return text ? '?' + text : '';
}

/**
 * Cliente de la API REST; todos los métodos devuelven una promesa con el JSON de respuesta.
 * @type {{get: function(string): Promise<any>, post: function(string, Object=): Promise<any>, put: function(string, Object=): Promise<any>, delete: function(string): Promise<any>}}
 * @example const { user } = await api.get('/me');
 */
export const api = {
  get: (path) => request('GET', path),
  post: (path, body = {}) => request('POST', path, body),
  put: (path, body = {}) => request('PUT', path, body),
  delete: (path) => request('DELETE', path),
};
