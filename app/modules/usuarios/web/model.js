// Users API calls and data shaping.
import { api, query, LIST_LIMIT } from '/js/core/api.js';

export const list = ({ q = '', rol = '', estado = '' } = {}) => api.get('/usuarios' + query({ q, rol, estado, limite: LIST_LIMIT }));
export const get = (id) => api.get('/usuarios/' + encodeURIComponent(id));
export const historial = (id) => api.get(`/usuarios/${encodeURIComponent(id)}/historial`);
export const syncPreview = () => api.get('/usuarios/actualizar');
export const syncApply = () => api.post('/usuarios/actualizar', {});
export const importCsv = (csv) => api.post('/usuarios/importar', { csv });
export const toggle = (id) => api.post(`/usuarios/${encodeURIComponent(id)}/toggle`);

export const save = (id, data) => {
  const body = {
    matricula: data.matricula.trim(),
    nombre_completo: data.nombre_completo.trim(),
    correo: data.correo.trim(),
    rol: data.rol,
    estado: data.estado,
    fuente_validacion: data.fuente_validacion,
    password: data.password || '',
  };
  return id ? api.put('/usuarios/' + encodeURIComponent(id), body) : api.post('/usuarios', body);
};

// Assignable roles (visitor is not a real account).
export async function roles() {
  try {
    return (await api.get('/roles')).roles;
  } catch {
    return [];
  }
}

export const roleMap = (roleList) => Object.fromEntries(roleList.map((r) => [r.nombre, r.descripcion]));

export const emptyUser = () => ({
  matricula: '', nombre_completo: '', correo: '', rol: 'alumno', estado: 'activo',
  fuente_validacion: 'servicios_escolares',
});
