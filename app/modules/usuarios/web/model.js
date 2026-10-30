/** @module modules/usuarios/model — llamadas a la API `/api/usuarios` y utilidades de datos para el módulo de usuarios */
import { api, query, LIST_LIMIT } from '/js/core/api.js';

/**
 * Lista usuarios con filtros. Llama a GET /api/usuarios (permiso `usuarios`).
 * @param {{q?: string, rol?: string, estado?: string}} [filters] - Búsqueda y filtros; se envía `limite` = LIST_LIMIT.
 * @returns {Promise<Object[]>} Cuentas con rol, préstamos activos y adeudos.
 */
export const list = ({ q = '', rol = '', estado = '' } = {}) => api.get('/usuarios' + query({ q, rol, estado, limite: LIST_LIMIT }));
/**
 * Obtiene una cuenta. Llama a GET /api/usuarios/:id.
 * @param {number|string} id - Identificador de la cuenta.
 * @returns {Promise<Object>} Cuenta.
 */
export const get = (id) => api.get('/usuarios/' + encodeURIComponent(id));
/**
 * Historial del usuario (RF-04). Llama a GET /api/usuarios/:id/historial.
 * @param {number|string} id - Identificador de la cuenta.
 * @returns {Promise<{prestamos: Object[], renovaciones: Object[], adeudos: Object[], espera: Object[], bitacora: Object[]}>}
 */
export const historial = (id) => api.get(`/usuarios/${encodeURIComponent(id)}/historial`);
/**
 * Vista previa de la actualización desde Servicios Escolares (D-23). Llama a GET /api/usuarios/actualizar.
 * @returns {Promise<{origen: string, registros: Object[], resumen: {nuevos: number, cambios: number, bajas: number}}>}
 */
export const syncPreview = () => api.get('/usuarios/actualizar');
/**
 * Aplica la actualización desde Servicios Escolares. Llama a POST /api/usuarios/actualizar.
 * @returns {Promise<{creados: number, actualizados: number, bajas: number, omitidos: Object[], credenciales_iniciales: Object[]}>}
 */
export const syncApply = () => api.post('/usuarios/actualizar', {});
/**
 * Importa una lista de alumnos en CSV (D-23). Llama a POST /api/usuarios/importar.
 * @param {string} csv - Contenido del CSV.
 * @returns {Promise<{creados: number, actualizados: number, bajas: number, errores: Object[], credenciales_iniciales: Object[]}>}
 */
export const importCsv = (csv) => api.post('/usuarios/importar', { csv });
/**
 * Da de baja o reactiva una cuenta. Llama a POST /api/usuarios/:id/toggle.
 * @param {number|string} id - Identificador de la cuenta.
 * @returns {Promise<Object>} Cuenta con su nuevo estado.
 */
export const toggle = (id) => api.post(`/usuarios/${encodeURIComponent(id)}/toggle`);

/**
 * Crea o edita una cuenta recortando espacios. Llama a PUT /api/usuarios/:id si hay `id`, si no a POST /api/usuarios.
 * @param {number|string|null} id - Id de la cuenta a editar; null/vacío para crear.
 * @param {Object} data - Datos del formulario.
 * @param {string} data.matricula - Matrícula o nómina.
 * @param {string} data.nombre_completo - Nombre completo.
 * @param {string} data.correo - Correo institucional.
 * @param {string} data.rol - Perfil.
 * @param {string} data.estado - 'activo' | 'inactivo'.
 * @param {string} data.fuente_validacion - Origen del registro.
 * @param {string} [data.password] - Contraseña (vacía al editar = conservar).
 * @returns {Promise<Object>} Cuenta guardada.
 */
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

/**
 * Perfiles asignables. Llama a GET /api/roles; ante error devuelve lista vacía.
 * @returns {Promise<Array<{nombre: string, descripcion: string}>>}
 */
export async function roles() {
  try {
    return (await api.get('/roles')).roles;
  } catch {
    return [];
  }
}

/**
 * Convierte la lista de perfiles en un mapa nombre -> descripción.
 * @param {Array<{nombre: string, descripcion: string}>} roleList - Perfiles.
 * @returns {Object<string, string>}
 */
export const roleMap = (roleList) => Object.fromEntries(roleList.map((r) => [r.nombre, r.descripcion]));

/**
 * Usuario vacío con valores por defecto para el formulario de alta.
 * @returns {{matricula: string, nombre_completo: string, correo: string, rol: string, estado: string, fuente_validacion: string}}
 */
export const emptyUser = () => ({
  matricula: '', nombre_completo: '', correo: '', rol: 'alumno', estado: 'activo',
  fuente_validacion: 'servicios_escolares',
});
