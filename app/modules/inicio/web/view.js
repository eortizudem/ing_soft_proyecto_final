import { html } from '/js/core/ui.js';
import { page, grid, linkCard, statCard, meter, notice, money, usd, date } from '/js/components/index.js';

const isStaff = (s) => !!s && s.usuarios_activos !== undefined;

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

const budget = (s) => meter({
  value: Number(s.presupuesto_usado_usd), max: Number(s.presupuesto_mensual_usd) || 1,
  label: 'Presupuesto de compras del mes (USD)',
  text: `${usd(s.presupuesto_usado_usd)} de ${usd(s.presupuesto_mensual_usd)}`,
});

// Estado propio (alumno/docente): préstamos, vencimientos y adeudos.
const ownCards = (m) => html`${m.prestamos_vencidos > 0 || m.adeudos_pendientes > 0
  ? notice({ tone: 'error', text: 'Tienes préstamos vencidos o multas pendientes: no podrás pedir nuevos préstamos hasta regularizarlos.' }) : ''}
  ${grid([
    statCard({ title: 'Mis préstamos activos', value: m.prestamos_activos,
      note: m.proximo_vencimiento ? `Próximo vencimiento: ${date(m.proximo_vencimiento)}` : 'Sin préstamos abiertos' }),
    statCard({ title: 'Préstamos vencidos', value: m.prestamos_vencidos, note: 'Devuélvelos en biblioteca' }),
    statCard({ title: 'Adeudos pendientes', value: money(m.adeudos_pendientes), note: 'Se pagan en Tesorería' }),
    statCard({ title: 'En lista de espera', value: m.espera_activa, note: 'Libros que esperas' }),
  ], { cols: 'stats' })}`;

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
