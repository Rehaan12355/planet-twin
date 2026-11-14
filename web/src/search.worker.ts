// Scores every cell of one world against a target and returns the best matches.

import type { Group, Meta, WorldName } from './data';
import { RELATIVE_TOLERANCE, distanceKm, percentile } from './score';

interface Held {
  meta: Meta;
  data: Float32Array;
  idx: Uint32Array | null;
  pct?: Float32Array; // percentile of every scored feature, built on first relative search
}

export interface SearchRequest {
  id: number;
  searchWorld: WorldName;
  target: number[]; // physical values, or percentiles in relative mode
  weights: Record<Group, number>;
  mode: 'physical' | 'relative';
  hideIce: boolean;
  barrenOnly: boolean;
  count: number;
  minSeparationKm: number;
}

export interface Match {
  row: number;
  cell: number;
  lat: number;
  lon: number;
  score: number;
}

export interface SearchResponse {
  id: number;
  scores: Float32Array; // one per row of the searched world; NaN where filtered out
  top: Match[];
  ms: number;
}

const worlds = new Map<WorldName, Held>();

function centre(meta: Meta, cell: number) {
  const row = Math.floor(cell / meta.cols);
  return { lat: 90 - (row + 0.5) * meta.cell_deg, lon: meta.lon0 + ((cell % meta.cols) + 0.5) * meta.cell_deg };
}

function percentiles(w: Held): Float32Array {
  if (w.pct) return w.pct;
  const nf = w.meta.features.length;
  const nc = w.meta.columns.length;
  const pct = new Float32Array(w.meta.n_rows * nf);
  w.meta.features.forEach((f, k) => {
    const c = w.meta.columns.indexOf(f.name);
    const q = w.meta.quantiles[f.name];
    for (let r = 0; r < w.meta.n_rows; r++) pct[r * nf + k] = percentile(q, w.data[r * nc + c]);
  });
  return (w.pct = pct);
}

function search(req: SearchRequest): SearchResponse {
  const t0 = performance.now();
  const w = worlds.get(req.searchWorld)!;
  const { meta } = w;
  const n = meta.n_rows;
  const nf = meta.features.length;
  const relative = req.mode === 'relative';
  const values = relative ? percentiles(w) : w.data;
  const stride = relative ? nf : meta.columns.length;
  const cols = meta.features.map((f, k) => (relative ? k : meta.columns.indexOf(f.name)));
  const inv = meta.features.map((f) => 1 / (relative ? RELATIVE_TOLERANCE : f.tolerance));
  const wts = meta.features.map((f) => req.weights[f.group]);
  const nc = meta.columns.length;
  const snowCol = meta.columns.indexOf('snow_frac');
  const ndviCol = meta.columns.indexOf('ndvi');
  const scores = new Float32Array(n);

  for (let r = 0; r < n; r++) {
    if (req.hideIce && snowCol >= 0 && w.data[r * nc + snowCol] >= 0.5) {
      scores[r] = NaN;
      continue;
    }
    if (req.barrenOnly && ndviCol >= 0 && !(w.data[r * nc + ndviCol] < 0.2)) {
      scores[r] = NaN;
      continue;
    }
    let sum = 0;
    let wsum = 0;
    const o = r * stride;
    for (let k = 0; k < nf; k++) {
      const t = req.target[k];
      const e = values[o + cols[k]];
      if (t !== t || e !== e) continue; // a missing feature is skipped, not scored as zero
      const d = (e - t) * inv[k];
      sum += wts[k] * Math.exp(-0.5 * d * d);
      wsum += wts[k];
    }
    scores[r] = wsum > 0 ? (100 * sum) / wsum : NaN;
  }

  // Greedy pick of the best rows that sit at least minSeparationKm apart.
  const order: number[] = [];
  let floor = 100;
  while (order.length < 4000 && floor > 0) {
    floor -= 5;
    order.length = 0;
    for (let r = 0; r < n; r++) if (scores[r] >= floor) order.push(r);
  }
  order.sort((a, b) => scores[b] - scores[a]);
  const top: Match[] = [];
  for (const r of order) {
    const cell = w.idx ? w.idx[r] : r;
    const c = centre(meta, cell);
    if (top.every((m) => distanceKm(m.lat, m.lon, c.lat, c.lon, meta.radius_km) >= req.minSeparationKm)) {
      top.push({ row: r, cell, lat: c.lat, lon: c.lon, score: scores[r] });
      if (top.length >= req.count) break;
    }
  }
  return { id: req.id, scores, top, ms: performance.now() - t0 };
}

self.onmessage = (e: MessageEvent) => {
  const msg = e.data;
  if (msg.type === 'init') {
    worlds.set(msg.world, { meta: msg.meta, data: msg.data, idx: msg.idx });
    return;
  }
  const res = search(msg as SearchRequest);
  (self as unknown as Worker).postMessage(res, [res.scores.buffer]);
};
