import { api } from '/js/core/api.js';

// Staff get global counts + `mio`; the rest only `mio` (own status). Errors -> null.
export async function stats() {
  try {
    return await api.get('/stats');
  } catch {
    return null;
  }
}
