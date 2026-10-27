// UI theme preference, stored only in localStorage.
const KEY = 'librigest-theme';
const DEFAULTS = { primary: '#1e68b8', background: '#f4f8fc', font: 'Roboto', logo: 'open' };

function read() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY)) };
  } catch {
    return { ...DEFAULTS };
  }
}

let current = read();

export const logoSrc = () => '/assets/' + (current.logo === 'stacked' ? 'logo-stacked.svg' : 'logo.svg');

export function apply() {
  const style = document.documentElement.style;
  style.setProperty('--primary', current.primary);
  style.setProperty('--bg', current.background);
  style.setProperty('--font', `'${current.font}',Arial,sans-serif`);
  document.querySelectorAll('.brand img').forEach((img) => { img.src = logoSrc(); });
}

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(current));
  } catch {
    /* storage unavailable: theme lasts for this page only */
  }
  apply();
}

export function set(patch) {
  current = { ...current, ...patch };
  save();
}

export function reset() {
  current = { ...DEFAULTS };
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  apply();
}
