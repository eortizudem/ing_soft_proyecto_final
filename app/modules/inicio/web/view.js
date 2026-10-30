/** @module modules/inicio/view — HTML puro del tablero de inicio (tarjetas de personal, estado propio y accesos) */
import { html } from '/js/core/ui.js';
import { page, grid, linkCard, statCard, meter, notice, money, usd, date } from '/js/components/index.js';

/**
 * Indica si las estadísticas son de personal (incluyen conteos globales).
 * @param {Object|null} s - Respuesta de /api/stats.
 * @returns {boolean}
 */
const isStaff = (s) => !!s && s.usuarios_activos !== undefined;

/**
 * Tarjetas de conteos globales del personal.
 * @param {{usuarios_activos: number, titulos_activos: number, compras_pendientes: number, prestamos_activos: number, prestamos_vencidos: number, adeudos_pendientes: number|string, espera_activa: number, consultas_pendientes: number}} s - Estadísticas globales.
 * @returns {*} Cuadrícula de tarjetas.
 */
const staffCards = (s) => grid([
  statCard({ title: 'Usuarios activos', value: s.usuarios_activos, note: 'Cuentas disponibles para consulta' }),
  statCard({ title: 'Títulos en catálogo', value: s.titulos_activos, note: 'Colección académica y literatura' }),
  statCard({ title: 'Solicitudes pendientes', value: s.compras_pendientes, note: 'Pendiente de Tesorería' }),
  statCard({ title: 'Préstamos activos', value: s.prestamos_activos, note: 'Ejemplares fuera de biblioteca' }),
  statCard({ title: 'Préstamos vencidos', value: s.prestamos_vencidos, note: 'Sin devolver después de su fecha' }),
  statCard({ title: 'Adeudos pendientes', value: money(s.adeudos_pendientes), note: 'Multas por cobrar' }),
  statCard({ title: 'En lista de espera', value: s.espera_activa, note: 'Usuarios esperando un ejemplar' }),
  statCard({ title: 'Consultas pendientes', value: s.consultas_pendientes, note: 'Preguntas del asistente que esperan a un bibliotecario' }),
], { cols: 'stats' });

/**
 * Medidor del presupuesto de compras del mes (D-22).
 * @param {{presupuesto_usado_usd: number|string, presupuesto_mensual_usd: number|string}} s - Estadísticas con presupuesto.
 * @returns {*}
 */
const budget = (s) => meter({
  value: Number(s.presupuesto_usado_usd), max: Number(s.presupuesto_mensual_usd) || 1,
  label: 'Presupuesto de compras del mes (USD)',
  text: `${usd(s.presupuesto_usado_usd)} de ${usd(s.presupuesto_mensual_usd)}`,
});

/**
 * Tarjetas del estado propio (préstamos, vencimientos, adeudos, espera) y aviso si hay vencidos o multas.
 * @param {{prestamos_activos: number, prestamos_vencidos: number, proximo_vencimiento: string|null, adeudos_pendientes: number|string, espera_activa: number}} m - Campo `mio` de /api/stats.
 * @returns {*}
 */
const ownCards = (m) => html`${m.prestamos_vencidos > 0 || m.adeudos_pendientes > 0
  ? notice({ tone: 'error', text: 'Tienes préstamos vencidos o multas pendientes: no podrás pedir nuevos préstamos hasta regularizarlos.' }) : ''}
  ${grid([
    statCard({ title: 'Mis préstamos activos', value: m.prestamos_activos,
      note: m.proximo_vencimiento ? `Próximo vencimiento: ${date(m.proximo_vencimiento)}` : 'Sin préstamos abiertos' }),
    statCard({ title: 'Préstamos vencidos', value: m.prestamos_vencidos, note: 'Devuélvelos en biblioteca' }),
    statCard({ title: 'Adeudos pendientes', value: money(m.adeudos_pendientes), note: 'Se pagan en Tesorería' }),
    statCard({ title: 'En lista de espera', value: m.espera_activa, note: 'Libros que esperas' }),
  ], { cols: 'stats' })}`;

/**
 * Tablero de inicio: tarjetas de personal o de estado propio, presupuesto (con permiso `compras`) y accesos rápidos según permisos.
 * @param {{nombre_completo: string, rol: string}} user - Usuario de la sesión.
 * @param {Object|null} stats - Respuesta de /api/stats (`mio` y, si es personal, conteos globales).
 * @param {(permiso: string) => boolean} can - Verifica permisos de la sesión.
 * @returns {*} Página (componente `page`).
 */
export const dashboard = (user, stats, can) => {
  const staff = isStaff(stats);
  const own = !staff && stats?.mio && user.rol !== 'visitante';
  return page({
    title: staff ? 'Una biblioteca bien organizada' : 'Explora tu biblioteca',
    desc: staff ? 'Gestiona personas, colecciones y nuevas adquisiciones desde un solo lugar.'
      : `Hola, ${user.nombre_completo}. Busca títulos, consulta disponibilidad y encuentra su ubicación.`,
    body: html`
  ${staff ? staffCards(stats) : ''}
  ${staff && can('compras') ? budget(stats) : ''}
  ${own ? ownCards(stats.mio) : ''}
  ${grid([
    can('buscar') && linkCard({ title: 'Buscar y localizar', text: 'Título, autor, editorial, tema o clave. Encuentra el pasillo y librero.', href: 'buscar' }),
    can('compras') && linkCard({ title: 'Solicitudes de compra', text: 'Prepara una solicitud y consulta su estado.', href: 'compras' }),
    can('usuarios') && linkCard({ title: 'Personas y permisos', text: 'Administra cuentas y funciones por perfil.', href: 'usuarios' }),
    can('catalogo') && linkCard({ title: 'Colección y ubicación', text: 'Mantén el catálogo actualizado y fácil de consultar.', href: 'catalogo' }),
    can('reportes') && linkCard({ title: 'Reportes', text: 'Consulta los listados y expórtalos a PDF o impresión.', href: 'reportes' }),
    can('guia') && linkCard({ title: 'Guía de demostración', text: 'Cuentas de prueba y preguntas frecuentes.', href: 'guia', full: true }),
  ])}`,
  });
};
