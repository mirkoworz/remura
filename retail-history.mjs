import { formatCapture } from './markets.mjs';

const dayMs = 24 * 60 * 60 * 1000;
const number = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 2 });
const signed = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 2, signDisplay: 'exceptZero' });
const shortDate = new Intl.DateTimeFormat('it-IT', { day: 'numeric', month: 'short', timeZone: 'Europe/Rome' });

function readSeries(archive) {
  if (archive?.schema !== 'remura-myfxbook-history-v1' || archive.source !== 'Myfxbook Community Outlook') {
    throw new Error('Formato storico Myfxbook inatteso');
  }
  const series = new Map();
  for (const [symbol, rows] of Object.entries(archive.symbols)) {
    if (!/^[A-Z0-9]{3,8}$/.test(symbol) || !Array.isArray(rows) || !rows.length) {
      throw new Error('Serie storica Myfxbook non valida');
    }
    let previous = -Infinity;
    series.set(symbol, rows.map(([time, long, short]) => {
      const timestamp = Date.parse(time);
      if (typeof time !== 'string' || !time.endsWith('Z') || !Number.isFinite(timestamp) ||
          timestamp <= previous || ![long, short].every(value => Number.isFinite(value) && value >= 0 && value <= 100)) {
        throw new Error('Rilevazione storica Myfxbook non valida');
      }
      previous = timestamp;
      return { timestamp, long, short };
    }));
  }
  if (!series.size) throw new Error('Archivio storico Myfxbook vuoto');
  return series;
}

function drawObservations(canvas, rows, palette) {
  const { width, height } = canvas.getBoundingClientRect();
  if (!width || !height || !rows.length) return;
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const context = canvas.getContext('2d');
  if (!context) return;
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.font = '11px system-ui, sans-serif';
  const left = 38, right = width - 10, top = 10, bottom = height - 24;
  const y = percentage => bottom - percentage * (bottom - top) / 100;
  for (const value of [0, 25, 50, 75, 100]) {
    context.strokeStyle = palette.grid;
    context.beginPath();
    context.moveTo(left, y(value));
    context.lineTo(right, y(value));
    context.stroke();
    context.fillStyle = palette.labels;
    context.textAlign = 'left';
    context.textBaseline = 'middle';
    context.fillText(value + '%', 1, y(value));
  }
  const first = rows[0].timestamp;
  const last = rows.at(-1).timestamp;
  const x = timestamp => last === first ? (left + right) / 2
    : left + 4 + (timestamp - first) * (right - left - 8) / (last - first);
  context.fillStyle = palette.point;
  for (const { timestamp, long } of rows) {
    context.beginPath();
    context.arc(x(timestamp), y(long), 3, 0, 2 * Math.PI);
    context.fill();
  }
  context.fillStyle = palette.labels;
  context.textAlign = first === last ? 'center' : 'left';
  context.fillText(shortDate.format(first), x(first), height - 10);
  if (first !== last) {
    context.textAlign = 'right';
    context.fillText(shortDate.format(last), x(last), height - 10);
  }
}

function renderHistory(root, series, archiveAsOf) {
  const symbol = root.querySelector('#history-symbol');
  const range = root.querySelector('#history-range');
  const view = root.querySelector('#history-view');
  const chart = root.querySelector('#history-chart');
  const summary = root.querySelector('#history-summary');
  const period = root.querySelector('#history-period');
  const detailTitle = root.querySelector('#history-detail-title');
  const table = root.querySelector('#history-rows');
  const styles = getComputedStyle(root);
  const palette = {
    grid: styles.getPropertyValue('--border').trim(),
    labels: styles.getPropertyValue('--muted').trim(),
    point: styles.getPropertyValue('--accent').trim(),
  };
  for (const name of [...series.keys()].sort()) symbol.add(new Option(name, name));
  if (series.has('EURUSD')) symbol.value = 'EURUSD';
  let selected = [];

  function draw() {
    drawObservations(chart, selected, palette);
  }

  function update() {
    const all = series.get(symbol.value);
    const last = all.at(-1);
    selected = range.value === '7' ? all.filter(row => row.timestamp >= last.timestamp - 7 * dayMs) : all;
    const first = selected[0];
    const observations = selected.length === 1 ? '1 rilevazione' : `${selected.length} rilevazioni`;
    const change = selected.length > 1 ? ` · ${signed.format(last.long - first.long)} pp tra prima e ultima` : '';
    summary.textContent = `${observations} · Ultimo long ${number.format(last.long)}% · short ${number.format(last.short)}%${change}`;
    period.textContent = selected.length === 1 ? formatCapture(last.timestamp)
      : `Dal ${formatCapture(first.timestamp)} al ${formatCapture(last.timestamp)} (ora italiana)`;
    if (archiveAsOf - last.timestamp > 48 * dayMs / 24) period.textContent += ' · Storico non recente rispetto allo snapshot del pacchetto (oltre 48 ore).';
    detailTitle.textContent = `Mostra rilevazioni (${selected.length})`;
    chart.setAttribute('aria-label', `Grafico ${symbol.value} della quota long, ${observations}`);
    const rows = document.createDocumentFragment();
    for (let index = selected.length - 1; index >= 0; index--) {
      const { timestamp, long, short } = selected[index];
      const row = document.createElement('tr');
      for (const value of [formatCapture(timestamp), number.format(long) + '%', number.format(short) + '%']) {
        row.insertCell().textContent = value;
      }
      rows.append(row);
    }
    table.replaceChildren(rows);
    draw();
  }

  view.hidden = false;
  symbol.addEventListener('change', update);
  range.addEventListener('change', update);
  new ResizeObserver(draw).observe(chart);
  update();
}

export async function mountRetailHistory(root) {
  const status = root.querySelector('#history-status');
  try {
    const response = await fetch(new URL('./data/myfxbook-history.json', import.meta.url), { mode: 'same-origin' });
    if (!response.ok) throw new Error('Archivio storico Myfxbook non disponibile');
    const archive = await response.json();
    const series = readSeries(archive);
    const archiveAsOf = Math.max(...[...series.values()].map(rows => rows.at(-1).timestamp));
    renderHistory(root, series, archiveAsOf);
    status.hidden = true;
  } catch {
    status.textContent = 'Archivio storico Myfxbook non disponibile. Ricarica la pagina per riprovare.';
  }
}
