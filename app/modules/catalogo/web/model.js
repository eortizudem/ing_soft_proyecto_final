/** @module modules/catalogo/model — llamadas a la API de libros/ejemplares y utilidades de datos del catálogo */
// Catalog API calls and data shaping.
import { api, query } from '/js/core/api.js';

// Field search (RF-12..15): `campo` picks which field `q` applies to; empty = every field.
/**
 * Campos de búsqueda disponibles (RF-12..15) como pares [valor, etiqueta]; '' = todos los campos.
 * @type {Array<[string, string]>}
 */
export const CAMPOS = [['', 'Todos los campos'], ['titulo', 'Título'], ['autor', 'Autor'], ['clave', 'Clave'],
  ['editorial', 'Editorial'], ['clasificacion', 'Clasificación']];
/**
 * Convierte texto y campo en parámetros de consulta: con `campo` filtra solo ese campo; sin él usa `q`.
 * @param {{q?: string, campo?: string}} filtros - Texto y campo elegido.
 * @returns {Object<string, string>} Parámetro de consulta (`{[campo]: q}` o `{q}`).
 */
const searchParams = ({ q = '', campo = '' }) => (campo ? { [campo]: q } : { q });

/**
 * Lista libros para administración. Llama a GET /api/libros.
 * @param {Object} [filtros] - Filtros opcionales.
 * @param {string} [filtros.q] - Texto libre.
 * @param {string} [filtros.campo] - Campo al que aplica `q` ('' = todos).
 * @param {string} [filtros.tema] - Tema.
 * @param {string} [filtros.estado] - 'activo' | 'inactivo' | ''.
 * @param {string} [filtros.tipo_uso] - Tipo de uso.
 * @param {string} [filtros.disponibilidad] - 'disponible' | 'agotado' | ''.
 * @returns {Promise<Object[]>} Libros.
 */
export const list = ({ q = '', campo = '', tema = '', estado = '', tipo_uso = '', disponibilidad = '' } = {}) =>
  api.get('/libros' + query({ ...searchParams({ q, campo }), tema, estado, tipo_uso, disponibilidad }));
/**
 * Obtiene un libro. Llama a GET /api/libros/:id.
 * @param {number|string} id - Id del libro.
 * @returns {Promise<Object>} Libro con ubicación y existencias.
 */
export const get = (id) => api.get('/libros/' + encodeURIComponent(id));
/**
 * Activa/inactiva un libro. Llama a POST /api/libros/:id/toggle.
 * @param {number|string} id - Id del libro.
 * @returns {Promise<Object>} Libro actualizado.
 */
export const toggle = (id) => api.post(`/libros/${encodeURIComponent(id)}/toggle`);

/**
 * Obtiene los temas del catálogo. Llama a GET /api/temas; ante error devuelve lista vacía.
 * @returns {Promise<string[]>} Temas.
 */
export async function themes() {
  try {
    return await api.get('/temas');
  } catch {
    return [];
  }
}

// Form fields (strings) -> API body. The server validates; we only convert types.
/**
 * Convierte los campos del formulario (cadenas) al cuerpo de la API y crea o actualiza el libro.
 * Llama a PUT /api/libros/:id si hay `id`, o POST /api/libros. El servidor valida; aquí solo se convierten tipos.
 * @param {number|string|null} id - Id del libro a editar; null/'' para crear.
 * @param {Object} f - Valores del formulario (clave, titulo, autor, editorial, tema, anio_publicacion, tipo_uso, clasificacion, sinopsis, precio_referencia, ejemplares, planta, pasillo, librero, nivel, estado, id_detalle).
 * @returns {Promise<Object>} Libro guardado.
 */
export function save(id, f) {
  const text = (k) => (f[k] || '').trim();
  const body = {
    clave: text('clave'), titulo: text('titulo'), autor: text('autor'), editorial: text('editorial'),
    tema: text('tema'), anio_publicacion: Number(f.anio_publicacion), tipo_uso: f.tipo_uso,
    clasificacion: text('clasificacion'), sinopsis: text('sinopsis'),
    precio_referencia: Number(f.precio_referencia), ejemplares: Number(f.ejemplares),
    planta: f.planta, pasillo: f.pasillo, librero: Number(f.librero), nivel: Number(f.nivel), estado: f.estado,
  };
  if (f.id_detalle) body.id_detalle = Number(f.id_detalle);
  return id ? api.put('/libros/' + encodeURIComponent(id), body) : api.post('/libros', body);
}

/**
 * Plantas disponibles para ubicar un libro.
 * @type {string[]}
 */
export const PLANTAS = ['Planta baja', 'Planta alta'];
/**
 * Letras de pasillo disponibles.
 * @type {string[]}
 */
export const PASILLOS = ['A', 'B', 'C', 'D', 'E', 'F'];
/**
 * Genera un rango entero inclusivo.
 * @param {number} from - Inicio.
 * @param {number} to - Fin.
 * @returns {number[]} Enteros de `from` a `to`.
 */
export const range = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => from + i);

/**
 * Libro vacío con valores por defecto para el formulario de alta.
 * @returns {Object} Libro con `ubicacion` anidada.
 */
export const emptyBook = () => ({
  clave: '', titulo: '', autor: '', editorial: '', tema: '', anio_publicacion: new Date().getFullYear(),
  tipo_uso: 'prestamo_externo', clasificacion: '', sinopsis: '', precio_referencia: 0, ejemplares: 1,
  estado: 'activo', ubicacion: { planta: 'Planta baja', pasillo: 'A', librero: 1, nivel: 1 },
});

// ---- Public search (buscar) ----
/**
 * Búsqueda pública de libros activos. Llama a GET /api/libros con estado=activo.
 * @param {Object} [filtros] - Filtros opcionales.
 * @param {string} [filtros.q] - Texto libre.
 * @param {string} [filtros.campo] - Campo al que aplica `q`.
 * @param {string} [filtros.tema] - Tema.
 * @param {string} [filtros.disponibilidad] - 'disponible' | 'agotado' | ''.
 * @param {string} [filtros.tipo_uso] - Tipo de uso.
 * @returns {Promise<Object[]>} Libros activos.
 */
export const search = ({ q = '', campo = '', tema = '', disponibilidad = '', tipo_uso = '' } = {}) =>
  api.get('/libros' + query({ ...searchParams({ q, campo }), tema, tipo_uso, estado: 'activo', disponibilidad }));

// ---- Ejemplares, etiqueta, pendientes, importación ----
/**
 * Lista ejemplares de un libro. Llama a GET /api/libros/:id/ejemplares.
 * @param {number|string} id - Id del libro.
 * @returns {Promise<Object[]>} Ejemplares con estado y préstamo activo.
 */
export const ejemplares = (id) => api.get(`/libros/${encodeURIComponent(id)}/ejemplares`);
/**
 * Da de baja un ejemplar. Llama a POST /api/ejemplares/:id/baja.
 * @param {number|string} idEjemplar - Id del ejemplar.
 * @param {string} motivo - perdido | robado | danado | obsoleto.
 * @param {string} [observacion] - Observación opcional.
 * @returns {Promise<Object>} Ejemplar actualizado.
 */
export const baja = (idEjemplar, motivo, observacion) =>
  api.post(`/ejemplares/${encodeURIComponent(idEjemplar)}/baja`, { motivo, observacion: observacion || undefined });
/**
 * Reactiva un ejemplar dado de baja. Llama a POST /api/ejemplares/:id/reactivar.
 * @param {number|string} idEjemplar - Id del ejemplar.
 * @returns {Promise<Object>} Ejemplar actualizado.
 */
export const reactivar = (idEjemplar) => api.post(`/ejemplares/${encodeURIComponent(idEjemplar)}/reactivar`, {});
/**
 * Obtiene ficha y etiquetas para imprimir. Llama a GET /api/libros/:id/etiqueta.
 * @param {number|string} id - Id del libro.
 * @returns {Promise<Object>} {clave, titulo, autor, clasificacion, ubicacion, codigo_ejemplares}.
 */
export const etiqueta = (id) => api.get(`/libros/${encodeURIComponent(id)}/etiqueta`);
/**
 * Lista líneas de compra recibidas sin catalogar. Llama a GET /api/libros/pendientes.
 * @returns {Promise<Object[]>} Líneas pendientes.
 */
export const pendientes = () => api.get('/libros/pendientes');
/**
 * Importa libros desde CSV. Llama a POST /api/libros/importar.
 * @param {string} csv - Contenido CSV con cabecera.
 * @returns {Promise<{creados: number, errores: Array<{linea: number, motivo: string}>}>} Resultado.
 */
export const importar = (csv) => api.post('/libros/importar', { csv });
