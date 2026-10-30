/** @module core/pdf — generador mínimo de PDF escrito a mano (Helvetica, A4, líneas de texto plano), sin librerías. */
/** @type {number} Máximo de caracteres por línea antes de partirla. */
const MAX_CHARS = 90;
/** @type {number} Líneas por página A4. */
const LINES_PER_PAGE = 46;

/**
 * Parte una línea larga en trozos de hasta MAX_CHARS, cortando en espacios cuando es posible.
 * @param {string} line - Línea original.
 * @returns {string[]} Líneas resultantes.
 */
function wrap(line) {
  const chunks = [];
  while (line.length > MAX_CHARS) {
    let cut = line.lastIndexOf(' ', MAX_CHARS);
    if (cut < 1) cut = MAX_CHARS;
    chunks.push(line.slice(0, cut));
    line = line.slice(cut).trim();
  }
  chunks.push(line);
  return chunks;
}

/**
 * Escapa una línea para una cadena literal PDF; los caracteres fuera de Latin-1 se sustituyen por "-".
 * @param {string} text - Texto original.
 * @returns {string} Texto escapado.
 */
const literal = (text) => text.replace(/[^\x20-\xFF]/g, '-').replace(/[\\()]/g, '\\$&');

/**
 * Construye un PDF (estructura de objetos, xref y trailer) a partir de líneas de texto.
 * @param {string[]} lines - Líneas de texto; se ajustan y paginan automáticamente.
 * @returns {Blob} Blob `application/pdf`.
 * @example const blob = buildPdf(['Comprobante', 'Libro: Dune']);
 */
export function buildPdf(lines) {
  const wrapped = lines.flatMap(wrap);
  const pages = [];
  for (let i = 0; i < wrapped.length; i += LINES_PER_PAGE) pages.push(wrapped.slice(i, i + LINES_PER_PAGE));

  // Object ids: 1 catalog, 2 pages, 3 font, then a (page, content) pair per page.
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
  ];
  pages.forEach((pageLines, n) => {
    const content = 'BT /F1 11 Tf 14 TL 42 795 Td ' +
      pageLines.map((l) => '(' + literal(l) + ') Tj T*').join('\n') + ' ET';
    objects.push(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents ${5 + n * 2} 0 R >>`,
      `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    );
  });
  objects[1] = `<< /Type /Pages /Count ${pages.length} /Kids [${pages.map((_, n) => `${4 + n * 2} 0 R`).join(' ')}] >>`;

  let pdf = '%PDF-1.4\n';
  const offsets = [];
  objects.forEach((body, n) => {
    offsets.push(pdf.length);
    pdf += `${n + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n` +
    offsets.map((o) => String(o).padStart(10, '0') + ' 00000 n \n').join('') +
    `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return new Blob([Uint8Array.from(pdf, (c) => c.charCodeAt(0) & 255)], { type: 'application/pdf' });
}

/**
 * Genera el PDF y dispara su descarga en el navegador.
 * @param {string[]} lines - Líneas de texto del documento.
 * @param {string} filename - Nombre del archivo descargado.
 * @returns {void}
 * @example downloadPdf(['Reporte de multas'], 'multas.pdf');
 */
export function downloadPdf(lines, filename) {
  const url = URL.createObjectURL(buildPdf(lines));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
