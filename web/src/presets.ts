import type { Group } from './data';

export type Weights = Record<Group, number>;

export interface Preset {
  id: string;
  label: string;
  weights: Weights;
}

export const PRESETS: Preset[] = [
  { id: 'balanced', label: 'Balanced', weights: { terrain: 1, temperature: 1, albedo: 1 } },
  { id: 'terrain', label: 'Terrain and mobility', weights: { terrain: 3, temperature: 0.5, albedo: 0.5 } },
  { id: 'thermal', label: 'Thermal hardware', weights: { terrain: 0.5, temperature: 3, albedo: 1 } },
];

export const GROUP_LABELS: Record<Group, string> = {
  terrain: 'Terrain',
  temperature: 'Temperature',
  albedo: 'Albedo',
};
