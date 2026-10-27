import { api } from '/js/core/api.js';

// -> { roles, permisos, matriz }
export const matrix = () => api.get('/roles');
export const setPermission = (rol, permiso, habilitado) =>
  api.put(`/roles/${encodeURIComponent(rol)}/permisos/${encodeURIComponent(permiso)}`, { habilitado });
