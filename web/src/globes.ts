import Globe from 'globe.gl';

export type GlobeInstance = ReturnType<typeof Globe>;

// Solid-colour placeholder until real NASA/USGS textures land in step 4.
function placeholderTexture(color: string): string {
  const canvas = document.createElement('canvas');
  canvas.width = 2;
  canvas.height = 1;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, 2, 1);
  return canvas.toDataURL();
}

export function createGlobe(el: HTMLElement, color: string): GlobeInstance {
  const globe = new Globe(el)
    .globeImageUrl(placeholderTexture(color))
    .backgroundColor('rgba(0,0,0,0)')
    .width(el.clientWidth)
    .height(el.clientWidth);
  new ResizeObserver(() => {
    globe.width(el.clientWidth).height(el.clientWidth);
  }).observe(el);
  return globe;
}
