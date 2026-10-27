// Tiny fetch wrapper. Same-origin, JSON in/out. Thrown errors: message, status, data and the payload fields (motivos...).
let unauthorizedHandler = null;

// Calls on these paths handle their own 401 (wrong password, no session yet).
const OWN_401 = ['/login', '/visitante', '/me', '/logout', '/recuperar', '/recuperar/confirmar'];

export function onUnauthorized(fn) {
  unauthorizedHandler = fn;
}

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

// Tope de filas de los listados administrativos grandes (usuarios, préstamos, multas); se envía como `limite`.
export const LIST_LIMIT = 500;

// Builds "?a=1&b=2" skipping empty values.
export function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== '' && value !== null && value !== undefined) search.set(key, value);
  }
  const text = search.toString();
  return text ? '?' + text : '';
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body = {}) => request('POST', path, body),
  put: (path, body = {}) => request('PUT', path, body),
  delete: (path) => request('DELETE', path),
};
