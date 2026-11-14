// Loads the per-world feature files written by pipeline/build_features.py.

export type WorldName = 'earth' | 'mars' | 'moon';
export type Group = 'terrain' | 'temperature' | 'albedo' | 'dryness';

export interface FeatureDef {
  name: string;
  label: string;
  unit: string;
  tolerance: number;
  group: Group;
  relative: boolean; // false for measurements that are zero everywhere on the target worlds
}

export interface Meta {
  world: WorldName;
  radius_km: number;
  cell_deg: number;
  cols: number;
  rows: number;
  lon0: number;
  columns: string[];
  n_rows: number;
  indexed: boolean;
  features: FeatureDef[];
  quantiles: Record<string, number[]>;
  sources: Record<string, string>;
  low_confidence_lat: number;
}

export interface World {
  meta: Meta;
  data: Float32Array; // n_rows x columns
  idx: Uint32Array | null; // flat cell index of each row (Earth land cells only)
  rowOfCell: Int32Array | null; // inverse of idx, -1 where there is no row
}

export interface Site {
  world: WorldName;
  site: string;
  lat: number;
  lon: number;
}

export interface Analog {
  site: string;
  lat: number;
  lon: number;
}

export type Place = [name: string, country: string, lat: number, lon: number];

const base = `${import.meta.env.BASE_URL}data/`;

async function buffer(name: string): Promise<ArrayBuffer> {
  const r = await fetch(base + name);
  if (!r.ok) throw new Error(`Could not load ${name} (HTTP ${r.status})`);
  return r.arrayBuffer();
}

export async function json<T>(name: string): Promise<T> {
  const r = await fetch(base + name);
  if (!r.ok) throw new Error(`Could not load ${name} (HTTP ${r.status})`);
  return r.json() as Promise<T>;
}

export async function loadWorld(name: WorldName): Promise<World> {
  const meta = await json<Meta>(`${name}.meta.json`);
  const [bin, idxBuf] = await Promise.all([
    buffer(`${name}.bin`),
    meta.indexed ? buffer(`${name}.idx.bin`) : Promise.resolve(null),
  ]);
  const data = new Float32Array(bin);
  if (data.length !== meta.n_rows * meta.columns.length) {
    throw new Error(`${name}.bin has ${data.length} values, expected ${meta.n_rows * meta.columns.length}`);
  }
  let idx: Uint32Array | null = null;
  let rowOfCell: Int32Array | null = null;
  if (idxBuf) {
    idx = new Uint32Array(idxBuf);
    rowOfCell = new Int32Array(meta.cols * meta.rows).fill(-1);
    for (let r = 0; r < idx.length; r++) rowOfCell[idx[r]] = r;
  }
  return { meta, data, idx, rowOfCell };
}

/** Flat cell index of a point. Longitude may be in either convention. */
export function cellOf(meta: Meta, lat: number, lon: number): number {
  const row = Math.min(Math.floor((90 - lat) / meta.cell_deg), meta.rows - 1);
  const col = Math.floor(((((lon - meta.lon0) % 360) + 360) % 360) / meta.cell_deg) % meta.cols;
  return Math.max(row, 0) * meta.cols + col;
}

export function cellCentre(meta: Meta, cell: number): { lat: number; lon: number } {
  const row = Math.floor(cell / meta.cols);
  const col = cell % meta.cols;
  return { lat: 90 - (row + 0.5) * meta.cell_deg, lon: meta.lon0 + (col + 0.5) * meta.cell_deg };
}

export function rowOf(world: World, cell: number): number {
  return world.rowOfCell ? world.rowOfCell[cell] : cell;
}

export function cellOfRow(world: World, row: number): number {
  return world.idx ? world.idx[row] : row;
}

/** One value by column name; NaN when the row or column is missing. */
export function valueAt(world: World, row: number, column: string): number {
  const c = world.meta.columns.indexOf(column);
  if (c < 0 || row < 0) return NaN;
  return world.data[row * world.meta.columns.length + c];
}

/** The scored feature values of one row, in meta.features order. */
export function featureVector(world: World, row: number): number[] {
  return world.meta.features.map((f) => valueAt(world, row, f.name));
}
