// Current user and permission checks.
import { api } from './api.js';

let user = null;

export const get = () => user;
export const set = (value) => { user = value; };
export const clear = () => { user = null; };
export const can = (permission) => !!user && user.permisos.includes(permission);
export const canAny = (list) => list.some(can);
export const isVisitor = () => user?.rol === 'visitante';

// Reloads the user from the server (also used after permission changes).
export async function load() {
  try {
    user = (await api.get('/me')).user;
  } catch {
    user = null;
  }
  return user;
}
