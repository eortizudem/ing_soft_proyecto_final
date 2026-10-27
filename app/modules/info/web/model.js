import { api } from '/js/core/api.js';
import { DEMO_ACCOUNTS } from '/m/auth/model.js';
import * as theme from '/js/core/theme.js';

export { DEMO_ACCOUNTS };

export async function faq() {
  try {
    return await api.get('/faq');
  } catch {
    return [];
  }
}

// Theme buttons: label + patch applied to the localStorage theme.
export const THEMES = [
  ['Azul', { primary: '#1e68b8' }],
  ['Verde', { primary: '#2e7d32' }],
  ['Morado', { primary: '#7251a6' }],
  ['Fondo frío', { background: '#f4f8fc' }],
  ['Fondo cálido', { background: '#fcf7ef' }],
  ['Fuente Roboto', { font: 'Roboto' }],
  ['Fuente Inter', { font: 'Inter' }],
  ['Libro abierto', { logo: 'open' }],
  ['Libros apilados', { logo: 'stacked' }],
];
export const applyTheme = (patch) => theme.set(patch);
export const resetTheme = () => theme.reset();

// Módulos del sistema: alimentan la Guía (accesos rápidos) y el Diagrama de funciones. `perm` oculta lo que el rol no usa.
export const MODULES = [
  { title: 'Acceso y personas', href: 'usuarios', perm: 'usuarios', button: 'Usuarios', text: 'Alta, edición, baja, historial y actualización de la lista desde Servicios Escolares.',
    items: ['Autenticación / visitante', 'Recuperar contraseña', 'Alta, edición y baja (se conserva el historial)', 'Historial del usuario', 'Actualizar desde Servicios Escolares e importar lista de alumnos (CSV)', 'Perfiles, permisos y políticas'] },
  { title: 'Catálogo y búsqueda', href: 'buscar', perm: 'buscar', button: 'Buscar y localizar', text: 'Búsqueda por campo y disponibilidad, ficha y ubicación web y móvil.',
    items: ['Registro, edición y baja de títulos', 'Ejemplares: baja y reactivación con motivo', 'Ficha bibliográfica y etiquetas (impresión y PDF)', 'Importación CSV y pendientes de catalogar', 'Búsqueda y filtros', 'Ubicación web y móvil'] },
  { title: 'Préstamos', href: 'prestamos', perm: 'prestamos', button: 'Préstamos', text: 'Préstamo con validación, renovación, devolución y recibo.',
    items: ['Nuevo préstamo con motivos de rechazo', 'Recibo imprimible y envío por correo o WhatsApp', 'Renovaciones y vencimiento en días hábiles', 'Devolución con multa por retraso', 'Pérdida y daño del ejemplar'] },
  { title: 'Lista de espera', href: 'espera', perm: 'espera', button: 'Lista de espera', text: 'Solicitudes por libro sin ejemplares y reservado al devolver.',
    items: ['Alta desde el rechazo del préstamo', 'Cancelación', 'Aviso al primero de la fila', 'Mis solicitudes (alumno y docente)'] },
  { title: 'Multas y pagos', href: 'adeudos', perm: 'adeudos', button: 'Multas y pagos', text: 'Pago con referencia de Tesorería, cancelar adeudos y reposición.',
    items: ['Registro de pago', 'Cancelar un adeudo (solo administrador)', 'Reposición por pérdida (USD × tipo de cambio)', 'Aviso a Servicios Escolares y Tesorería'] },
  { title: 'Compras', href: 'compras', perm: 'compras', button: 'Compras', text: 'Solicitud a Tesorería con presupuesto, recibir el pedido y factura.',
    items: ['Medidor de presupuesto mensual', 'Solicitud, envío y cancelación', 'Recibir el pedido completo o por partes, con factura', 'Líneas pendientes de catalogar'] },
  { title: 'Reportes y avisos', href: 'reportes', perm: 'reportes', button: 'Reportes', text: 'Catálogo, usuarios, alumnos con adeudos, inventario por estante, vencidos y préstamos.',
    items: ['Vista previa, PDF e impresión', 'Alumnos con adeudos, con aviso a Servicios Escolares', 'Indicadores (asistente, inventario, préstamos)', 'Errores del sistema'] },
  { title: 'Notificaciones', href: 'notificaciones', perm: 'notificaciones', button: 'Notificaciones', text: 'Avisos enviados (simulados): correo, WhatsApp, Servicios Escolares y Tesorería.',
    items: ['Lista del personal con filtros', 'Mis notificaciones (alumno y docente)', 'Avisos de entrega, libro reservado y multas'] },
  { title: 'Asistente virtual', href: 'asistente', perm: 'asistente', button: 'Asistente', text: 'Preguntas frecuentes, búsqueda de libros y pasar la consulta a un bibliotecario.',
    items: ['Horarios y política de préstamo', 'Búsqueda de libros y mis préstamos', 'Pasar a bibliotecario y opinión (¿te ayudó?)', 'Versión móvil'] },
];
