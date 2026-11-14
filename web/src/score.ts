// The match score. Shared by the search worker and the passport so both show the same numbers.

export const RELATIVE_TOLERANCE = 10; // percentile points

/** Gaussian closeness of two values given a tolerance: 1 when equal, falling towards 0. */
export function match(a: number, b: number, tolerance: number): number {
  const d = (a - b) / tolerance;
  return Math.exp(-0.5 * d * d);
}

/** Percentile (0 to 100) of a value within a world, from its 101-point quantile table. */
export function percentile(quantiles: number[], v: number): number {
  if (Number.isNaN(v)) return NaN;
  if (v <= quantiles[0]) return 0;
  if (v >= quantiles[100]) return 100;
  let lo = 0;
  let hi = 100;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (quantiles[mid] <= v) lo = mid;
    else hi = mid;
  }
  const span = quantiles[hi] - quantiles[lo];
  return lo + (span > 0 ? (v - quantiles[lo]) / span : 0);
}

/** Great-circle distance in km on a sphere of the given radius. */
export function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number, radiusKm: number): number {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * radiusKm * Math.asin(Math.min(1, Math.sqrt(a)));
}
