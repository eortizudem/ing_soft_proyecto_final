// Catalog API calls and data shaping.
import { api, query } from '/js/core/api.js';

// Field search (RF-12..15): `campo` picks which field `q` applies to; empty = every field.
export const CAMPOS = [['', 'Todos los campos'], ['titulo', 'Título'], ['autor', 'Autor'], ['clave', 'Clave'],
  ['editorial', 'Editorial'], ['clasificacion', 'Clasificación']];
const searchParams = ({ q = '', campo = '' }) => (campo ? { [campo]: q } : { q });

export const list = ({ q = '', campo = '', tema = '', estado = '', tipo_uso = '', disponibilidad = '' } = {}) =>
  api.get('/libros' + query({ ...searchParams({ q, campo }), tema, estado, tipo_uso, disponibilidad }));
export const get = (id) => api.get('/libros/' + encodeURIComponent(id));
export const toggle = (id) => api.post(`/libros/${encodeURIComponent(id)}/toggle`);

export async function themes() {
  try {
    return await api.get('/temas');
  } catch {
    return [];
  }
}

// Form fields (strings) -> API body. The server validates; we only convert types.
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

export const PLANTAS = ['Planta baja', 'Planta alta'];
export const PASILLOS = ['A', 'B', 'C', 'D', 'E', 'F'];
export const range = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => from + i);

export const emptyBook = () => ({
  clave: '', titulo: '', autor: '', editorial: '', tema: '', anio_publicacion: new Date().getFullYear(),
  tipo_uso: 'prestamo_externo', clasificacion: '', sinopsis: '', precio_referencia: 0, ejemplares: 1,
  estado: 'activo', ubicacion: { planta: 'Planta baja', pasillo: 'A', librero: 1, nivel: 1 },
});

// ---- Public search (buscar) ----
export const search = ({ q = '', campo = '', tema = '', disponibilidad = '', tipo_uso = '' } = {}) =>
  api.get('/libros' + query({ ...searchParams({ q, campo }), tema, tipo_uso, estado: 'activo', disponibilidad }));

// ---- Ejemplares, etiqueta, pendientes, importación ----
export const ejemplares = (id) => api.get(`/libros/${encodeURIComponent(id)}/ejemplares`);
export const baja = (idEjemplar, motivo, observacion) =>
  api.post(`/ejemplares/${encodeURIComponent(idEjemplar)}/baja`, { motivo, observacion: observacion || undefined });
export const reactivar = (idEjemplar) => api.post(`/ejemplares/${encodeURIComponent(idEjemplar)}/reactivar`, {});
export const etiqueta = (id) => api.get(`/libros/${encodeURIComponent(id)}/etiqueta`);
export const pendientes = () => api.get('/libros/pendientes');
export const importar = (csv) => api.post('/libros/importar', { csv });
