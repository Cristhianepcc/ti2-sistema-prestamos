// Gráficos de Reportes (RF6): SVG/HTML hechos a mano, sin librería externa —
// mismo criterio que ICONOS en shell.js. Funciones puras: reciben datos ya
// calculados por el backend y devuelven HTML, nada de estado propio. Quien
// llama es responsable de pasar texto ya escapado con esc() donde corresponda
// (nombres/códigos de recurso son datos de usuario).

function _fechaCortaChart(iso) {
  const [anio, mes, dia] = String(iso).slice(0, 10).split("-").map(Number);
  return new Date(anio, mes - 1, dia).toLocaleDateString("es-PE", { day: "numeric", month: "short" });
}

// segmentos: [{ label, valor, color }] — color como var(--token) del design system.
function donutChartHTML(segmentos, { tamano = 140, grosor = 18 } = {}) {
  const total = segmentos.reduce((suma, seg) => suma + seg.valor, 0);
  const r = (tamano - grosor) / 2;
  const centro = tamano / 2;
  const circunferencia = 2 * Math.PI * r;

  let arcos;
  if (total === 0) {
    arcos = `<circle cx="${centro}" cy="${centro}" r="${r}" fill="none" stroke="var(--linea)" stroke-width="${grosor}" />`;
  } else {
    let acumulado = 0;
    arcos = segmentos
      .filter((seg) => seg.valor > 0)
      .map((seg) => {
        const largo = (seg.valor / total) * circunferencia;
        const offset = -acumulado;
        acumulado += largo;
        return `<circle cx="${centro}" cy="${centro}" r="${r}" fill="none" stroke="${seg.color}"
          stroke-width="${grosor}" stroke-dasharray="${largo.toFixed(2)} ${(circunferencia - largo).toFixed(2)}"
          stroke-dashoffset="${offset.toFixed(2)}" transform="rotate(-90 ${centro} ${centro})" />`;
      })
      .join("");
  }

  const leyenda = segmentos
    .map(
      (seg) =>
        `<li><span class="chart-dot" style="background:${seg.color}"></span>${esc(seg.label)}<b>${esc(seg.valor)}</b></li>`
    )
    .join("");

  return `<div class="chart-donut">
    <svg width="${tamano}" height="${tamano}" viewBox="0 0 ${tamano} ${tamano}" class="chart-svg" style="width:${tamano}px">${arcos}</svg>
    <ul class="chart-legend">${leyenda}</ul>
  </div>`;
}

// puntos: [{ fecha: "YYYY-MM-DD", prestamos, devoluciones }], ya ordenados.
function lineChartHTML(puntos) {
  if (!puntos || puntos.length === 0) {
    return `<p class="nota-futura">Sin datos para graficar.</p>`;
  }

  const ancho = 640;
  const alto = 200;
  const pad = 28;
  const max = Math.max(1, ...puntos.flatMap((p) => [p.prestamos, p.devoluciones]));
  const n = puntos.length;
  const pasoX = n > 1 ? (ancho - pad * 2) / (n - 1) : 0;
  const coordY = (valor) => alto - pad - (valor / max) * (alto - pad * 2);
  const coordX = (i) => pad + i * pasoX;

  const trazo = (campo) =>
    puntos
      .map((p, i) => `${i === 0 ? "M" : "L"}${coordX(i).toFixed(1)},${coordY(p[campo]).toFixed(1)}`)
      .join(" ");

  const indicesEtiqueta = n === 1 ? [0] : [...new Set([0, Math.floor((n - 1) / 2), n - 1])];
  const etiquetas = indicesEtiqueta
    .map((i) => {
      const anchor = i === 0 ? "start" : i === n - 1 ? "end" : "middle";
      return `<text x="${coordX(i).toFixed(1)}" y="${alto - 6}" class="chart-eje" text-anchor="${anchor}">${esc(_fechaCortaChart(puntos[i].fecha))}</text>`;
    })
    .join("");

  const lineasGrid = [0, 0.5, 1]
    .map((f) => {
      const yy = (pad + f * (alto - pad * 2)).toFixed(1);
      return `<line x1="${pad}" y1="${yy}" x2="${ancho - pad}" y2="${yy}" class="chart-grid" />`;
    })
    .join("");

  return `<div class="chart-linea">
    <div class="chart-legend chart-legend-inline">
      <span><span class="chart-dot" style="background:var(--azul)"></span>Préstamos</span>
      <span><span class="chart-dot" style="background:var(--verde)"></span>Devoluciones</span>
    </div>
    <svg viewBox="0 0 ${ancho} ${alto}" class="chart-svg">
      ${lineasGrid}
      <path d="${trazo("prestamos")}" fill="none" stroke="var(--azul)" stroke-width="2" />
      <path d="${trazo("devoluciones")}" fill="none" stroke="var(--verde)" stroke-width="2" />
      ${etiquetas}
    </svg>
  </div>`;
}

// items: [{ label, sub?, valor, color? }] — barras horizontales, ancho proporcional al máximo.
function barChartHTML(items, { color = "var(--azul)" } = {}) {
  if (!items || items.length === 0) {
    return `<p class="nota-futura">Sin datos para graficar.</p>`;
  }
  const max = Math.max(...items.map((it) => it.valor), 1);
  return `<div class="chart-barras">
    ${items
      .map((it) => {
        const pct = Math.round((it.valor / max) * 100);
        return `<div class="chart-barra-fila">
          <div class="chart-barra-etiqueta">
            <span class="t">${esc(it.label)}</span>${it.sub ? `<span class="s">${esc(it.sub)}</span>` : ""}
          </div>
          <div class="chart-barra-pista"><div class="chart-barra-valor" style="width:${pct}%;background:${it.color || color}"></div></div>
          <b class="chart-barra-total">${esc(it.valor)}</b>
        </div>`;
      })
      .join("")}
  </div>`;
}
