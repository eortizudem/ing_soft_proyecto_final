/** @module modules/auth/model — llamadas a la API de autenticación (`/api/login`, `/api/visitante`, `/api/logout`, `/api/recuperar*`) y cuentas demo. */
import { api } from '/js/core/api.js';

/**
 * Cuentas de la semilla (app/seed.py); `nota` describe el escenario demo de cada una. `boton` es la etiqueta opcional del botón de acceso rápido.
 * @type {Array<{rol: string, matricula: string, password: string, nota: string, boton?: string}>}
 */
export const DEMO_ACCOUNTS = [
  { rol: 'Administrador', matricula: 'ADM001', password: 'Admin123', nota: 'Todo, incluida la cancelación de adeudos' },
  { rol: 'Bibliotecario', matricula: 'BIB001', password: 'Biblioteca123', nota: 'Préstamos, lista de espera, adeudos y notificaciones' },
  { rol: 'Catálogo', matricula: 'CAT001', password: 'Catalogo123', nota: 'Catálogo, ejemplares, etiquetas y reportes' },
  { rol: 'Comprador', matricula: 'COM001', password: 'Compras123', nota: 'Pedidos de compra y recibir pedidos' },
  { rol: 'Colaborador', matricula: 'COL001', password: 'Colabora123', nota: 'Catálogo, compras y reportes' },
  { rol: 'Alumno', matricula: 'A0512345', password: 'Alumno123', boton: 'Alumno (María)', nota: 'María: 1 préstamo activo y en lista de espera' },
  { rol: 'Alumno', matricula: 'A0512980', password: 'Alumno123', boton: 'Alumno (Carlos)', nota: 'Carlos: préstamo vencido sin devolver' },
  { rol: 'Alumno', matricula: 'A0513001', password: 'Alumno123', boton: 'Alumno (Laura)', nota: 'Laura: adeudo por retraso pendiente (no puede pedir prestado)' },
  { rol: 'Docente', matricula: 'DOC001', password: 'Docente123', nota: '3 préstamos activos (límite del docente)' },
];

/**
 * Inicia sesión (POST /api/login).
 * @param {string} matricula - matrícula o número de colaborador (se recorta).
 * @param {string} password - contraseña.
 * @returns {Promise<object>} usuario público (`user`).
 */
export const login = async (matricula, password) =>
  (await api.post('/login', { matricula: matricula.trim(), password })).user;
/**
 * Inicia sesión de visitante (POST /api/visitante).
 * @returns {Promise<object>} usuario visitante (`user`).
 */
export const visitor = async () => (await api.post('/visitante')).user;
/**
 * Cierra la sesión (POST /api/logout).
 * @returns {Promise<object>} `{ok: true}`.
 */
export const logout = () => api.post('/logout');
/**
 * Solicita el código de recuperación (POST /api/recuperar). La respuesta incluye `token` solo con `DEMO_MOSTRAR_TOKEN` activo.
 * @param {string} correo - correo institucional (se recorta).
 * @returns {Promise<{ok: boolean, token?: string|null}>}
 */
export const requestReset = (correo) => api.post('/recuperar', { correo: correo.trim() });
/**
 * Cambia la contraseña con el código recibido (POST /api/recuperar/confirmar).
 * @param {string} token - código de recuperación (se recorta).
 * @param {string} password - nueva contraseña (mínimo 6 caracteres).
 * @returns {Promise<object>} `{ok: true}`.
 */
export const confirmReset = (token, password) => api.post('/recuperar/confirmar', { token: token.trim(), password });
