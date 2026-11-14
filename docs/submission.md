# Submission draft

DRAFT for the team to edit. Every number here comes from `web/public/data/validation.json`
and the live site on 14 November 2026. Re-check them if the data is rebuilt.

## Project name

Planet Twin

## High-level summary

Planet Twin is a search engine across three worlds. Click any spot on Mars or the Moon and an
Earth globe spins to the land that is most like it, chosen from 342,571 cells about 30 km wide.
Each match comes with an analog passport: five measurements side by side in real units, a
score out of 100, the ways the analogy breaks, and what a mission could test there. All the
matching runs in the browser on NASA data from MOLA, TES, LOLA, Diviner, MERRA-2, CERES and
MODIS. We also tested the engine against 15 famous analog sites and publish the result, which
was a failure, together with what it teaches.

## Links

- Live site: https://rehaan12355.github.io/planet-twin/
- Code: https://github.com/Rehaan12355/planet-twin
- Demo: to be recorded (30 seconds, English subtitles)

## Detailed project description

**The problem.** Mission teams test hardware and procedures at a small number of famous
places such as the Atacama, Devon Island and Hawaii. Those sites were found one at a time and
have never been compared with the rest of the planet in a systematic way.

**The method.** Earth, Mars and the Moon are cut into cells of nearly the same ground size,
about 30 km. Every cell gets the same five measurements: mean slope and local relief from
laser altimetry, mean surface temperature, day-night temperature range, and albedo. A match
is scored with one transparent formula and fixed tolerances in real units. Three presets
(Balanced, Terrain and mobility, Thermal hardware) reweight the score for different tests.
A search over all of Earth's land takes about 30 milliseconds in a Web Worker.

**What it found.** With temperature included, nowhere on Earth is much like Mars. Mars targets
average about 210 K with a swing of about 80 K between day and night, so the best Earth cells
reach about 60 out of 100: terrain and albedo match, and temperature scores zero. For Jezero
Crater the closest terrain-and-albedo matches are dry basins in south-east Iran, the Chilean
Puna beside the Atacama, Oman and northern Chad. For Gale Crater it is the Tian Shan foothills
of north-west China. Under the Thermal hardware preset with ice allowed, the answer is
Antarctica. These are candidate regions for field checks, not discoveries.

**The evidence, including the part that failed.** The engine was never told about 15 famous
analog sites. Across ten Mars targets it placed 7% of them in the best 10% of Earth's land
with the Balanced preset, 5% with Terrain and mobility and 6% with Thermal hardware. Chance
gives 10%. We tried the one tolerance change our plan allowed and it did not help, so we kept
the original values. The engine does pass its internal checks: an Earth cell matched against
Earth returns itself with a score of 100, and every data reader puts known landmarks in the
right place. Our reading: five coarse physical measurements do not rediscover sites that
experts chose for minerals, water chemistry, microbes and road access.

**The limits.** A 30 km cell describes a region, not a crater or a lava tube. Temperature
comes from different kinds of source on each world: a reanalysis on Earth, a climate model on
Mars, a radiometer on the Moon. Lunar south-pole sites fall in the grid's low-confidence
zone. Earth cannot copy low gravity, a thin or absent atmosphere, or the radiation. Every
passport says so.

**How it could help a mission.** As a first filter: given a landing site and a purpose, it
lists regions whose slopes, relief and brightness match, and shows plainly how far each falls
short on temperature. The hometown mode turns the same engine into an outreach tool.

## NASA data used

Copy the "NASA data" table from DATA_SOURCES.md.

## Space agency partner and other data

ETOPO 2022 (NOAA NCEI), Natural Earth land polygons and populated places. Tools: Python
(numpy, scipy, rasterio, xarray), Vite, TypeScript, globe.gl, three.js.

## AI use

Copy from AI_USE.md after checking it is still true.

## Still to do by the team

- [ ] Confirm the 2026 demo format and the local deadline
- [ ] Check the site coordinates in `pipeline/sites/*.csv` against published sources (all are marked `verified=no`)
- [ ] Research the top surprise sites: what is really at 28.9 N, 61.1 E in Iran and 25.1 S, 68.9 W in Chile
- [ ] Record the 30-second demo: click Jezero Crater, open the passport, then type a hometown
- [ ] Add team members to README.md and this file
- [ ] Test every link in a private browser window
