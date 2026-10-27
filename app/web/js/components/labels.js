// Single source of truth for enum display labels and badge tones.
// Add a new state here and every table, badge, filter and form picks it up.

/** label per kind/value. */
export const LABELS = {
  estadoUsuario: { activo: 'Activa', inactivo: 'Inactiva' },
  estadoLibro: { activo: 'Activo', inactivo: 'Inactivo' },
  fuente: {
    servicios_escolares: 'Servicios Escolares',
    recursos_humanos: 'Recursos Humanos',
    manual: 'Alta manual',
  },
  tipoUso: { prestamo_externo: 'Préstamo externo', consulta_interna: 'Consulta interna', reservado: 'Reservado' },
  solicitud: { pendiente: 'Pendiente', enviada: 'Enviada a Tesorería', recibida: 'Recibida', cancelada: 'Cancelada' },
  disponibilidad: { disponible: 'Disponible', agotado: 'Sin copias disponibles', baja: 'Dado de baja', prestado: 'Prestado' },
  // Circulación (préstamos, adeudos, lista de espera), baja de ejemplares, notificaciones y asistente.
  prestamo: { activo: 'Activo', devuelto: 'Devuelto', vencido: 'Vencido' },
  adeudo: { pendiente: 'Pendiente', pagado: 'Pagado', cancelado: 'Cancelado' },
  adeudoTipo: { retraso: 'Retraso', danio: 'Daño', perdida: 'Pérdida' },
  listaEspera: { en_espera: 'En espera', notificado: 'Notificado', recogido: 'Recogido', cancelado: 'Cancelado' },
  motivoBaja: { perdido: 'Perdido', robado: 'Robado', danado: 'Dañado', obsoleto: 'Obsoleto' },
  canal: { email: 'Correo', whatsapp: 'WhatsApp', servicios_escolares: 'Servicios Escolares', tesoreria: 'Tesorería' },
  canalChat: { web: 'Web', movil: 'Móvil' },
  emisor: { usuario: 'Usuario', asistente: 'Asistente' },
  consulta: { pendiente: 'Pendiente', resuelta: 'Atendida' },
  // Actualización / importación de lista de alumnos (usuarios) y alta masiva.
  accionSync: { nuevo: 'Alta', cambio: 'Modificación', baja: 'Baja', sin_cambios: 'Sin cambios', omitido: 'Omitido' },
};

/** badge tone per kind/value: 'good' (default green) | 'warn' | 'bad'. */
export const TONES = {
  estadoUsuario: { inactivo: 'bad' },
  estadoLibro: { inactivo: 'bad' },
  solicitud: { pendiente: 'warn', cancelada: 'bad' },
  disponibilidad: { agotado: 'warn', baja: 'bad', prestado: 'warn' },
  prestamo: { vencido: 'bad' },
  adeudo: { pendiente: 'warn' },
  motivoBaja: { perdido: 'bad', robado: 'bad', danado: 'warn', obsoleto: 'warn' },
  consulta: { pendiente: 'warn' },
  listaEspera: { en_espera: 'warn', cancelado: 'bad' },
  accionSync: { cambio: 'warn', baja: 'bad', omitido: 'bad' },
};

export const label = (kind, value) => LABELS[kind]?.[value] || value || '';
export const labelItems = (kind) => Object.entries(LABELS[kind] || {});
export const tone = (kind, value) => TONES[kind]?.[value] || 'good';

/** Fallback role names when the API has not loaded them. */
export const ROLES = {
  admin: 'Administrador', alumno: 'Alumno', docente: 'Docente', catalogo: 'Catálogo',
  comprador: 'Comprador', bibliotecario: 'Bibliotecario', visitante: 'Visitante', colaborador: 'Colaborador',
};
export const roleName = (map, rol) => map?.[rol] || ROLES[rol] || rol;
