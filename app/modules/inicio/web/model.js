/** @module modules/inicio/model — llamada a la API del tablero de inicio */
import { api } from '/js/core/api.js';

/**
 * Estadísticas del tablero. Llama a GET /api/stats (requiere sesión). El personal recibe conteos globales y `mio`; el resto solo `mio` (estado propio).
 * @returns {Promise<Object|null>} Estadísticas, o null si la petición falla.
 */
export async function stats() {
  try {
    return await api.get('/stats');
  } catch {
    return null;
  }
}
