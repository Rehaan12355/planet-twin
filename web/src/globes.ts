import Globe from 'globe.gl';
import { CanvasTexture, Color, SRGBColorSpace } from 'three';
import type { MeshPhongMaterial } from 'three';

export interface Pin {
  lat: number;
  lon: number;
  kind: 'target' | 'rank' | 'analog' | 'city';
  label: string;
  title: string;
  selected?: boolean;
  onClick?: () => void;
}

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

/** globe.gl wants longitude in -180..180. */
const lng = (lon: number) => ((((lon + 180) % 360) + 360) % 360) - 180;

/** One globe with a paintable surface: a base texture plus an optional heat overlay. */
export class WorldGlobe {
  private globe: InstanceType<typeof Globe>;
  private canvas = document.createElement('canvas');
  private texture = new CanvasTexture(this.canvas);
  private base: HTMLImageElement | null = null;
  private heat: HTMLCanvasElement | null = null;

  constructor(el: HTMLElement, atmosphere: string | null, onClick: (lat: number, lon: number) => void) {
    this.canvas.width = 4096;
    this.canvas.height = 2048;
    this.texture.colorSpace = SRGBColorSpace;
    this.globe = new Globe(el, { animateIn: false })
      .backgroundColor('rgba(0,0,0,0)')
      .showAtmosphere(atmosphere !== null)
      .atmosphereColor(atmosphere ?? '#ffffff')
      .atmosphereAltitude(0.12)
      .width(el.clientWidth)
      .height(el.clientHeight)
      .htmlElementsData([])
      .htmlLat((d) => (d as Pin).lat)
      .htmlLng((d) => lng((d as Pin).lon))
      .htmlAltitude(0.01)
      .htmlElement((d) => pinElement(d as Pin));
    const material = this.globe.globeMaterial() as MeshPhongMaterial;
    material.map = this.texture;
    material.color = new Color(0xffffff);
    material.needsUpdate = true;
    this.globe.pointOfView({ lat: 15, lng: 0, altitude: 2.1 });
    new ResizeObserver(() => this.globe.width(el.clientWidth).height(el.clientHeight)).observe(el);

    // globe.gl only reports a click after it has seen the pointer hover, so the first click
    // after load and most taps on a phone are lost. Detect a press without a drag ourselves.
    let down: { x: number; y: number; t: number } | null = null;
    el.addEventListener('pointerdown', (e) => {
      down = { x: e.clientX, y: e.clientY, t: performance.now() };
    });
    el.addEventListener('pointerup', (e) => {
      if (!down || (e.target as HTMLElement).closest('.pin')) return;
      const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y);
      const held = performance.now() - down.t;
      down = null;
      if (moved > 5 || held > 600) return; // that was a drag to rotate
      const box = el.getBoundingClientRect();
      const hit = this.globe.toGlobeCoords(e.clientX - box.left, e.clientY - box.top);
      if (hit) onClick(hit.lat, hit.lng);
    });
  }

  async setTexture(url: string): Promise<void> {
    const img = new Image();
    img.src = url;
    await img.decode();
    this.base = img;
    this.paint();
  }

  setHeat(heat: HTMLCanvasElement | null): void {
    this.heat = heat;
    this.paint();
  }

  setPins(pins: Pin[]): void {
    this.globe.htmlElementsData(pins);
  }

  flyTo(lat: number, lon: number, altitude = 1.5): void {
    this.globe.pointOfView({ lat, lng: lng(lon), altitude }, reducedMotion.matches ? 0 : 1800);
  }

  private paint(): void {
    const ctx = this.canvas.getContext('2d')!;
    const { width, height } = this.canvas;
    if (this.base) ctx.drawImage(this.base, 0, 0, width, height);
    else {
      ctx.fillStyle = '#2a3142';
      ctx.fillRect(0, 0, width, height);
    }
    if (this.heat) ctx.drawImage(this.heat, 0, 0, width, height);
    this.texture.needsUpdate = true;
  }
}

function pinElement(pin: Pin): HTMLElement {
  const el = document.createElement(pin.onClick ? 'button' : 'div');
  el.className = `pin pin-${pin.kind}${pin.selected ? ' is-selected' : ''}`;
  el.title = pin.title;
  el.setAttribute('aria-label', pin.title);
  el.textContent = pin.label;
  if (pin.onClick) {
    el.style.pointerEvents = 'auto';
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      pin.onClick!();
    });
  }
  return el;
}
