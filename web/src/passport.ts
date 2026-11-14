// The analog passport: the scorecard that says how two places match and where they do not.

import type { FeatureDef, World, WorldName } from './data';
import { cellCentre, cellOfRow, valueAt } from './data';
import { RELATIVE_TOLERANCE, match, percentile } from './score';
import type { Weights } from './presets';

export interface PassportInput {
  mode: 'physical' | 'relative';
  target: World; // Mars or the Moon
  targetRow: number;
  targetName: string;
  earth: World;
  earthRow: number;
  earthName: string;
  score: number;
  weights: Weights;
}

const BODY: Record<'mars' | 'moon', { name: string; gravity: number; air: string; radiation: string }> = {
  mars: {
    name: 'Mars',
    gravity: 3.71,
    air: 'about 6 hPa of carbon dioxide, under 1% of Earth’s',
    radiation: 'about 0.67 mSv a day at the surface, measured by Curiosity',
  },
  moon: {
    name: 'the Moon',
    gravity: 1.62,
    air: 'a vacuum',
    radiation: 'about 1.4 mSv a day at the surface, measured by Chang’e 4',
  },
};

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);
const ordinal = (v: number) => {
  const n = Math.round(v);
  const tail = n % 100 >= 11 && n % 100 <= 13 ? 'th' : (['th', 'st', 'nd', 'rd'][n % 10] ?? 'th');
  return `${n}${tail}`;
};
const num = (v: number, digits = 0) => v.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits });

export function formatValue(f: FeatureDef, v: number): string {
  if (Number.isNaN(v)) return 'no data';
  switch (f.name) {
    case 'mean_slope':
      return `${num(v, 1)}°`;
    case 'local_relief':
      return `${num(Math.round(10 ** v))} m`;
    case 'mean_temp':
      return `${num(v)} K (${num(v - 273.15)} °C)`;
    case 'diurnal_range':
      return `${num(v)} K`;
    case 'rain_mm':
      return `${num(v)} mm`;
    default:
      return num(v, 2);
  }
}

export function formatCoords(lat: number, lon: number, world: WorldName): string {
  const ns = `${num(Math.abs(lat), 1)}° ${lat >= 0 ? 'N' : 'S'}`;
  if (world === 'earth') {
    const x = ((((lon + 180) % 360) + 360) % 360) - 180;
    return `${ns}, ${num(Math.abs(x), 1)}° ${x >= 0 ? 'E' : 'W'}`;
  }
  return `${ns}, ${num(((lon % 360) + 360) % 360, 1)}° E`;
}

const TESTS: Record<string, string> = {
  mean_slope: 'Rover mobility and traverse planning: the slopes here are close to the target’s.',
  local_relief: 'Route finding and line-of-sight communications: the ups and downs across the cell are on the same scale.',
  mean_temp: 'Cold-soak tests of batteries, lubricants and seals: the yearly mean surface temperature is close.',
  diurnal_range: 'Thermal cycling of hardware: the swing between day and night is close to the target’s.',
  albedo: 'Camera exposure, navigation imaging and solar heating: the ground reflects a similar share of sunlight.',
  rain_mm: 'Dust, dry-soil handling and long unattended deployments: it almost never rains here.',
  ndvi: 'Sampling and imaging of bare rock and soil: almost nothing grows here.',
};

export function renderPassport(el: HTMLElement, p: PassportInput): void {
  const targetWorld = p.target.meta.world as 'mars' | 'moon';
  const body = BODY[targetWorld];
  const tc = cellCentre(p.target.meta, cellOfRow(p.target, p.targetRow));
  const ec = cellCentre(p.earth.meta, cellOfRow(p.earth, p.earthRow));
  const relative = p.mode === 'relative';

  const rows = p.earth.meta.features.filter((f) => !relative || f.relative).map((f) => {
    const t = valueAt(p.target, p.targetRow, f.name);
    const e = valueAt(p.earth, p.earthRow, f.name);
    const missing = Number.isNaN(t) || Number.isNaN(e);
    let m = NaN;
    let tPct = NaN;
    let ePct = NaN;
    if (relative) {
      tPct = percentile(p.target.meta.quantiles[f.name], t);
      ePct = percentile(p.earth.meta.quantiles[f.name], e);
      if (!missing) m = match(ePct, tPct, RELATIVE_TOLERANCE);
    } else if (!missing) m = match(e, t, f.tolerance);
    return { f, t, e, m, missing, tPct, ePct, weight: p.weights[f.group] };
  });

  const featureRows = rows
    .map((r) => {
      const pct = (v: number) => (relative && !Number.isNaN(v) ? `<small>${ordinal(v)} percentile</small>` : '');
      const bar = r.missing
        ? '<span class="missing">missing, left out of the score</span>'
        : `<span class="bar" role="img" aria-label="${num(r.m * 100)} out of 100"><i style="width:${(r.m * 100).toFixed(0)}%"></i></span><b>${num(r.m * 100)}</b>`;
      return `<tr${r.weight === 0 ? ' class="unweighted"' : ''}>
        <th scope="row">${esc(r.f.label)}</th>
        <td>${formatValue(r.f, r.t)}${pct(r.tPct)}</td>
        <td>${formatValue(r.f, r.e)}${pct(r.ePct)}</td>
        <td class="match">${bar}</td></tr>`;
    })
    .join('');

  const weak = rows.filter((r) => !r.missing && r.m < 0.3);
  const strong = rows.filter((r) => !r.missing && r.m >= 0.6).sort((a, b) => b.m - a.m);
  const snow = valueAt(p.earth, p.earthRow, 'snow_frac');

  const breaks: string[] = weak.map(
    (r) => `${esc(r.f.label)}: ${formatValue(r.f, r.e)} here against ${formatValue(r.f, r.t)} on ${body.name}.`,
  );
  if (!Number.isNaN(snow) && snow >= 0.05) breaks.push(`Snow lies on the ground about ${num(snow * 100)}% of the year.`);
  breaks.push(`Gravity: 9.81 m/s² here against ${body.gravity} m/s² on ${body.name}. No place on Earth changes that.`);
  breaks.push(`Air: about 1,013 hPa at sea level here against ${body.air}.`);
  breaks.push(`Radiation: about 2.4 mSv a year of natural background here against ${body.radiation}.`);

  const tests = strong.slice(0, 2).map((r) => TESTS[r.f.name]);
  const lowConfidence = Math.abs(tc.lat) > p.target.meta.low_confidence_lat;
  const trek = `https://trek.nasa.gov/${targetWorld}/#v=0.1&x=${(((tc.lon + 180) % 360) - 180).toFixed(3)}&y=${tc.lat.toFixed(3)}&z=5`;
  const ex = ((((ec.lon + 180) % 360) + 360) % 360) - 180;
  const worldview = `https://worldview.earthdata.nasa.gov/?v=${(ex - 3).toFixed(2)},${(ec.lat - 2).toFixed(2)},${(ex + 3).toFixed(2)},${(ec.lat + 2).toFixed(2)}`;

  el.innerHTML = `
    <header class="passport-head">
      <div>
        <p class="doc-type">Analog passport${relative ? ', relative match' : ''}</p>
        <h3>${esc(p.earthName)}</h3>
        <p class="route">${formatCoords(ec.lat, ec.lon, 'earth')} on Earth, matched to ${esc(p.targetName)} (${formatCoords(tc.lat, tc.lon, targetWorld)})</p>
      </div>
      <div class="stamp" aria-label="Overall score ${num(p.score)} out of 100"><b>${num(p.score)}</b><span>out of 100</span></div>
    </header>
    ${relative ? '<p class="notice">Relative match. This compares where each value ranks within its own world, not the real values. Your town is not physically like Mars.</p>' : ''}
    ${lowConfidence ? '<p class="notice">Low confidence. This target lies within 5° of a pole, where this grid distorts slopes and temperatures are poorly sampled.</p>' : ''}
    <table class="features">
      <thead><tr><th scope="col">Measurement</th><th scope="col">${esc(body.name === 'the Moon' ? 'Moon' : 'Mars')}</th><th scope="col">Earth</th><th scope="col">Match</th></tr></thead>
      <tbody>${featureRows}</tbody>
    </table>
    <section>
      <h4>Where it breaks</h4>
      <ul>${breaks.map((b) => `<li>${b}</li>`).join('')}</ul>
    </section>
    <section>
      <h4>What you could test here</h4>
      ${tests.length ? `<ul>${tests.map((t) => `<li>${t}</li>`).join('')}</ul>` : '<p>No measurement matches closely enough to recommend a test here.</p>'}
    </section>
    <p class="links"><a href="${worldview}" target="_blank" rel="noopener">See the Earth site in NASA Worldview</a><a href="${trek}" target="_blank" rel="noopener">See the target in NASA ${targetWorld === 'mars' ? 'Mars' : 'Moon'} Trek</a></p>
    <p class="caveat">A candidate for field checks, not a discovery. Each cell is about 30 km wide, so it describes a region and cannot confirm one crater, cave or lava tube.</p>`;
  el.hidden = false;
}
