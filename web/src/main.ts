import type { Analog, Group, Place, Site, World, WorldName } from './data';
import { cellOf, cellOfRow, featureVector, json, loadWorld, rowOf } from './data';
import type { Pin } from './globes';
import { WorldGlobe } from './globes';
import { formatCoords, renderPassport } from './passport';
import type { Weights } from './presets';
import { GROUP_LABELS, PRESETS } from './presets';
import { distanceKm, percentile } from './score';
import type { Match, SearchRequest, SearchResponse } from './search.worker';

type Target = Exclude<WorldName, 'earth'>;
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const textures = `${import.meta.env.BASE_URL}textures/`;
const MIN_SEPARATION_KM = 300;

const status = $('status');
const resultsEl = $<HTMLOListElement>('results');
const passportEl = $('passport');
const siteSelect = $<HTMLSelectElement>('site-select');
const cityInput = $<HTMLInputElement>('city-input');

const worlds = {} as Record<WorldName, World>;
let sites: Site[] = [];
let analogs: Analog[] = [];
let places: Place[] = [];

const state = {
  targetWorld: 'mars' as Target,
  target: null as { lat: number; lon: number; name: string; row: number } | null,
  weights: { ...PRESETS[0].weights } as Weights,
  matches: [] as Match[],
  selected: 0,
  city: null as { place: Place; row: number } | null, // set while showing a hometown twin
};

const worker = new Worker(new URL('./search.worker.ts', import.meta.url), { type: 'module' });
let requestId = 0;
const pending = new Map<number, (r: SearchResponse) => void>();
worker.onmessage = (e: MessageEvent<SearchResponse>) => {
  pending.get(e.data.id)?.(e.data);
  pending.delete(e.data.id);
};
function search(req: Omit<SearchRequest, 'id'>): Promise<SearchResponse> {
  const id = ++requestId;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    worker.postMessage({ ...req, id });
  });
}

const targetGlobe = new WorldGlobe($('target-globe'), null, (lat, lon) => pickTarget(lat, lon));
const earthGlobe = new WorldGlobe($('earth-globe'), '#8fc7ff', () => {});

// ---- Loading

async function start(): Promise<void> {
  void targetGlobe.setTexture(`${textures}mars.jpg`);
  void earthGlobe.setTexture(`${textures}earth.jpg`);
  const [earth, mars, moon, siteFile, placeFile] = await Promise.all([
    loadWorld('earth'),
    loadWorld('mars'),
    loadWorld('moon'),
    json<{ targets: Site[]; analogs: Analog[] }>('sites.json'),
    json<Place[]>('places.json'),
  ]);
  Object.assign(worlds, { earth, mars, moon });
  for (const w of [earth, mars, moon]) {
    worker.postMessage({ type: 'init', world: w.meta.world, meta: w.meta, data: w.data, idx: w.idx });
  }
  sites = siteFile.targets;
  analogs = siteFile.analogs;
  places = placeFile;
  buildControls();
  status.textContent = 'Click anywhere on Mars to find its twin on Earth.';
}

// ---- Controls

function buildControls(): void {
  document.querySelectorAll<HTMLButtonElement>('[data-world]').forEach((b) => {
    b.addEventListener('click', () => setTargetWorld(b.dataset.world as Target));
  });
  fillSites();
  siteSelect.addEventListener('change', () => {
    const s = sites.find((x) => x.world === state.targetWorld && x.site === siteSelect.value);
    if (s) pickTarget(s.lat, s.lon, s.site);
  });

  const presets = $('presets');
  const sliders = $('sliders');
  for (const p of PRESETS) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = p.label;
    b.dataset.preset = p.id;
    b.setAttribute('aria-pressed', String(p.id === 'balanced'));
    b.addEventListener('click', () => {
      state.weights = { ...p.weights };
      syncWeights(p.id);
      void runSearch();
    });
    presets.append(b);
  }
  for (const g of Object.keys(GROUP_LABELS) as Group[]) {
    const label = document.createElement('label');
    label.innerHTML = `<span>${GROUP_LABELS[g]}</span><input type="range" min="0" max="3" step="0.5" data-group="${g}" /><output></output>`;
    const input = label.querySelector('input')!;
    input.addEventListener('input', () => {
      state.weights[g] = Number(input.value);
      syncWeights(null);
      void runSearch();
    });
    sliders.append(label);
  }
  syncWeights('balanced');

  for (const id of ['filter-ice', 'filter-barren']) $(id).addEventListener('change', () => void runSearch());
  $('show-heat').addEventListener('change', () => void runSearch());
  $('show-analogs').addEventListener('change', drawPins);

  const list = $('city-list');
  cityInput.addEventListener('input', () => {
    const q = cityInput.value.trim().toLowerCase();
    if (q.length < 2) return;
    const hits = places.filter((p) => p[0].toLowerCase().startsWith(q)).slice(0, 12);
    list.replaceChildren(...hits.map((p) => new Option(`${p[0]}, ${p[1]}`)));
    const exact = hits.find((p) => `${p[0]}, ${p[1]}`.toLowerCase() === q);
    if (exact) void hometown(exact);
  });
  cityInput.addEventListener('change', () => {
    const q = cityInput.value.trim().toLowerCase();
    if (!q) return;
    const hit = places.find((p) => `${p[0]}, ${p[1]}`.toLowerCase() === q) ?? places.find((p) => p[0].toLowerCase() === q);
    if (hit) void hometown(hit);
    else status.textContent = `No city called “${cityInput.value}” in the list. Try a larger town nearby.`;
  });
}

function syncWeights(presetId: string | null): void {
  document.querySelectorAll<HTMLButtonElement>('[data-preset]').forEach((b) => {
    b.setAttribute('aria-pressed', String(b.dataset.preset === presetId));
  });
  document.querySelectorAll<HTMLInputElement>('[data-group]').forEach((i) => {
    const v = state.weights[i.dataset.group as Group];
    i.value = String(v);
    (i.nextElementSibling as HTMLOutputElement).textContent = `×${v}`;
  });
}

function fillSites(): void {
  const options = sites.filter((s) => s.world === state.targetWorld).map((s) => new Option(s.site));
  siteSelect.replaceChildren(new Option('Choose a site', ''), ...options);
}

function setTargetWorld(world: Target, keep = false): void {
  if (world === state.targetWorld && !keep) return;
  state.targetWorld = world;
  document.querySelectorAll<HTMLButtonElement>('[data-world]').forEach((b) => {
    b.setAttribute('aria-pressed', String(b.dataset.world === world));
  });
  const name = world === 'mars' ? 'Mars' : 'Moon';
  $('target-title').textContent = name;
  void targetGlobe.setTexture(`${textures}${world}.jpg`);
  fillSites();
  if (!keep) {
    state.target = null;
    state.city = null;
    state.matches = [];
    resultsEl.hidden = true;
    passportEl.hidden = true;
    earthGlobe.setHeat(null);
    $('heat-legend').hidden = true;
    drawPins();
    status.textContent = `Click anywhere on ${world === 'mars' ? 'Mars' : 'the Moon'} to find its twin on Earth.`;
  }
}

// ---- Find a twin (physical match)

function pickTarget(lat: number, lon: number, name?: string): void {
  if (!worlds.earth) return;
  const w = worlds[state.targetWorld];
  const cell = cellOf(w.meta, lat, lon);
  if (!name) siteSelect.value = '';
  state.city = null;
  cityInput.value = '';
  state.target = {
    lat,
    lon,
    row: rowOf(w, cell),
    name: name ?? (state.targetWorld === 'mars' ? 'Mars' : 'the Moon'),
  };
  $('target-hint').textContent = `Pin at ${formatCoords(lat, lon, state.targetWorld)}`;
  if (name) targetGlobe.flyTo(lat, lon);
  void runSearch(true);
}

async function runSearch(fly = true): Promise<void> {
  if (state.city) return hometown(state.city.place);
  if (!state.target) return;
  const w = worlds[state.targetWorld];
  const res = await search({
    searchWorld: 'earth',
    target: featureVector(w, state.target.row),
    weights: state.weights,
    mode: 'physical',
    hideIce: $<HTMLInputElement>('filter-ice').checked,
    barrenOnly: $<HTMLInputElement>('filter-barren').checked,
    count: 5,
    minSeparationKm: MIN_SEPARATION_KM,
  });
  state.matches = res.top;
  state.selected = 0;
  const showHeat = $<HTMLInputElement>('show-heat').checked;
  earthGlobe.setHeat(showHeat ? heatCanvas(worlds.earth, res.scores) : null);
  $('heat-legend').hidden = !showHeat;
  if (!res.top.length) {
    status.textContent = 'No land cell passes the current filters. Turn a filter off and try again.';
    resultsEl.hidden = true;
    passportEl.hidden = true;
    drawPins();
    return;
  }
  status.textContent = `Scored ${worlds.earth.meta.n_rows.toLocaleString('en-US')} land cells in ${res.ms.toFixed(0)} ms. Best five, at least ${MIN_SEPARATION_KM} km apart:`;
  showResults();
  select(0, fly);
}

function showResults(): void {
  resultsEl.replaceChildren(
    ...state.matches.map((m, i) => {
      const li = document.createElement('li');
      const b = document.createElement('button');
      b.type = 'button';
      b.innerHTML = `<span class="score">${m.score.toFixed(0)}</span><span class="where"><b>${placeName(m.lat, m.lon)}</b><small>${formatCoords(m.lat, m.lon, 'earth')}</small></span>`;
      b.addEventListener('click', () => select(i, true));
      li.append(b);
      return li;
    }),
  );
  resultsEl.hidden = false;
}

function select(i: number, fly: boolean): void {
  state.selected = i;
  const m = state.matches[i];
  resultsEl.querySelectorAll('button').forEach((b, k) => b.setAttribute('aria-current', String(k === i)));
  drawPins();
  if (fly) earthGlobe.flyTo(m.lat, m.lon);
  renderPassport(passportEl, {
    mode: 'physical',
    target: worlds[state.targetWorld],
    targetRow: state.target!.row,
    targetName: state.target!.name,
    earth: worlds.earth,
    earthRow: m.row,
    earthName: placeName(m.lat, m.lon),
    score: m.score,
    weights: state.weights,
  });
}

// ---- Hometown twin (relative match against Mars)

async function hometown(place: Place): Promise<void> {
  const earth = worlds.earth;
  const row = nearestLandRow(place[2], place[3]);
  if (row < 0) {
    status.textContent = `${place[0]} sits too far from mapped land to compare.`;
    return;
  }
  setTargetWorld('mars', true);
  state.city = { place, row };
  const target = earth.meta.features.map((f, k) => percentile(earth.meta.quantiles[f.name], featureVector(earth, row)[k]));
  const res = await search({
    searchWorld: 'mars',
    target,
    weights: state.weights,
    mode: 'relative',
    hideIce: false,
    barrenOnly: false,
    count: 1,
    minSeparationKm: 0,
  });
  const twin = res.top[0];
  if (!twin) return;
  state.matches = [];
  state.target = { lat: twin.lat, lon: twin.lon, row: twin.row, name: 'Mars' };
  resultsEl.hidden = true;
  earthGlobe.setHeat(null);
  $('heat-legend').hidden = true;
  $('target-hint').textContent = `Twin of ${place[0]} at ${formatCoords(twin.lat, twin.lon, 'mars')}`;
  status.textContent = `${place[0]}’s twin on Mars, by rank within each world. This is a relative match, for fun.`;
  drawPins();
  earthGlobe.flyTo(place[2], place[3]);
  targetGlobe.flyTo(twin.lat, twin.lon);
  renderPassport(passportEl, {
    mode: 'relative',
    target: worlds.mars,
    targetRow: twin.row,
    targetName: state.target.name,
    earth,
    earthRow: row,
    earthName: `${place[0]}, ${place[1]}`,
    score: twin.score,
    weights: state.weights,
  });
}

/** Row of the land cell at a point, or the closest land cell within two cells (coastal cities). */
function nearestLandRow(lat: number, lon: number): number {
  const { meta } = worlds.earth;
  let best = -1;
  let bestD = Infinity;
  for (let dy = -2; dy <= 2; dy++) {
    for (let dx = -2; dx <= 2; dx++) {
      const la = Math.max(-89.9, Math.min(89.9, lat + dy * meta.cell_deg));
      const row = rowOf(worlds.earth, cellOf(meta, la, lon + dx * meta.cell_deg));
      const d = dx * dx + dy * dy;
      if (row >= 0 && d < bestD) {
        best = row;
        bestD = d;
      }
    }
  }
  return best;
}

// ---- Pins, place names, heat layer

function drawPins(): void {
  const targetPins: Pin[] = [];
  const earthPins: Pin[] = [];
  if (state.target) {
    targetPins.push({ lat: state.target.lat, lon: state.target.lon, kind: 'target', label: '', title: state.target.name });
  }
  state.matches.forEach((m, i) => {
    earthPins.push({
      lat: m.lat,
      lon: m.lon,
      kind: 'rank',
      label: String(i + 1),
      title: `Match ${i + 1}: ${placeName(m.lat, m.lon)}, score ${m.score.toFixed(0)}`,
      selected: i === state.selected,
      onClick: () => select(i, true),
    });
  });
  if (state.city) {
    const p = state.city.place;
    earthPins.push({ lat: p[2], lon: p[3], kind: 'city', label: '', title: `${p[0]}, ${p[1]}` });
  }
  if ($<HTMLInputElement>('show-analogs').checked) {
    for (const a of analogs) {
      earthPins.push({ lat: a.lat, lon: a.lon, kind: 'analog', label: '', title: `Known analog site: ${a.site}` });
    }
  }
  targetGlobe.setPins(targetPins);
  earthGlobe.setPins(earthPins);
}

/** A readable name for a spot on Earth: the nearest listed town and how far away it is. */
function placeName(lat: number, lon: number): string {
  let best: Place | null = null;
  let bestD = Infinity;
  for (const p of places) {
    if (Math.abs(p[2] - lat) > 12) continue;
    const d = distanceKm(lat, lon, p[2], p[3], 6371);
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }
  if (!best) return `Remote land at ${formatCoords(lat, lon, 'earth')}`;
  const km = Math.round(bestD / 10) * 10;
  return km < 30 ? `Near ${best[0]}, ${best[1]}` : `${km} km from ${best[0]}, ${best[1]}`;
}

// Score 40 fades in as deep violet; 100 is pale yellow.
const RAMP: [number, number, number][] = [
  [72, 40, 140],
  [176, 48, 150],
  [240, 96, 80],
  [250, 176, 60],
  [255, 244, 170],
];

function heatCanvas(earth: World, scores: Float32Array): HTMLCanvasElement {
  const { cols, rows } = earth.meta;
  const canvas = document.createElement('canvas');
  canvas.width = cols;
  canvas.height = rows;
  const ctx = canvas.getContext('2d')!;
  const img = ctx.createImageData(cols, rows);
  for (let r = 0; r < scores.length; r++) {
    const s = scores[r];
    if (!(s > 40)) continue;
    const t = Math.min(1, (s - 40) / 60);
    const x = t * (RAMP.length - 1);
    const i = Math.min(RAMP.length - 2, Math.floor(x));
    const f = x - i;
    const o = cellOfRow(earth, r) * 4;
    for (let c = 0; c < 3; c++) img.data[o + c] = RAMP[i][c] + (RAMP[i + 1][c] - RAMP[i][c]) * f;
    img.data[o + 3] = 70 + 170 * t;
  }
  ctx.putImageData(img, 0, 0);
  return canvas;
}

start().catch((e: Error) => {
  status.textContent = `${e.message}. Reload the page to try again.`;
  status.classList.add('is-error');
});
