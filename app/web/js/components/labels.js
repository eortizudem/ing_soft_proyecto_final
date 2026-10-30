/**
 * @module components/labels — única fuente de verdad de las etiquetas de enumeraciones y los tonos de insignia.
 * Al añadir un estado nuevo aquí, toda tabla, insignia, filtro y formulario lo adopta.
 */

/**
 * Etiqueta visible por tipo y valor almacenado.
 * @type {Object<string, Object<string,string>>}
 */
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

/**
 * Tono de insignia por tipo y valor: 'good' (verde, por defecto) | 'warn' | 'bad'.
 * @type {Object<string, Object<string,string>>}
 */
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

/**
 * Etiqueta visible de un valor.
 * @param {string} kind - Tipo (clave de `LABELS`).
 * @param {string} value - Valor almacenado.
 * @returns {string} Etiqueta, o el propio valor si no está definida (vacío si no hay valor).
 */
export const label = (kind, value) => LABELS[kind]?.[value] || value || '';
/**
 * Pares `[valor, etiqueta]` de un tipo, listos para `options()` o filtros.
 * @param {string} kind - Tipo (clave de `LABELS`).
 * @returns {Array<Array<string>>} Pares valor/etiqueta (vacío si el tipo no existe).
 */
export const labelItems = (kind) => Object.entries(LABELS[kind] || {});
/**
 * Tono de insignia de un valor.
 * @param {string} kind - Tipo (clave de `TONES`).
 * @param {string} value - Valor almacenado.
 * @returns {string} 'good' | 'warn' | 'bad' ('good' por defecto).
 */
export const tone = (kind, value) => TONES[kind]?.[value] || 'good';

/**
 * Nombres de rol de respaldo cuando la API aún no los ha cargado.
 * @type {Object<string,string>}
 */
export const ROLES = {
  admin: 'Administrador', alumno: 'Alumno', docente: 'Docente', catalogo: 'Catálogo',
  comprador: 'Comprador', bibliotecario: 'Bibliotecario', visitante: 'Visitante', colaborador: 'Colaborador',
};
/**
 * Nombre visible de un rol.
 * @param {?Object<string,string>} map - Nombres cargados desde la API (puede ser nulo).
 * @param {string} rol - Clave del rol.
 * @returns {string} Nombre del mapa, de `ROLES` o la propia clave.
 */
export const roleName = (map, rol) => map?.[rol] || ROLES[rol] || rol;
