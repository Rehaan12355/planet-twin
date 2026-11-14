# Submission draft

DRAFT for the team to edit. Every number here comes from `web/public/data/validation.json`
and the live site on 14 November 2026. Re-check them if the data is rebuilt.

## Project name

Planet Twin

## High-level summary

Planet Twin is a search engine across three worlds. Click any spot on Mars or the Moon and an
Earth globe spins to the land that is most like it, chosen from 342,571 cells about 30 km wide.
Each match comes with an analog passport: seven measurements side by side in real units, a
score out of 100, the ways the analogy breaks, and what a mission could test there. All the
matching runs in the browser on NASA data from MOLA, TES, LOLA, Diviner, MERRA-2, CERES and
MODIS. We also tested the engine against 15 famous analog sites and publish the whole story: a first
version that failed, the change we made, and a second result that is modestly above chance.

## Links

- Live site: https://rehaan12355.github.io/planet-twin/
- Code: https://github.com/Rehaan12355/planet-twin
- Demo: to be recorded (30 seconds, English subtitles)

## Detailed project description

**The problem.** Mission teams test hardware and procedures at a small number of famous
places such as the Atacama, Devon Island and Hawaii. Those sites were found one at a time and
have never been compared with the rest of the planet in a systematic way.

**The method.** Earth, Mars and the Moon are cut into cells of nearly the same ground size,
about 30 km. Every cell gets the same seven measurements: mean slope and local relief from
laser altimetry, mean surface temperature, day-night temperature range, albedo, yearly
rainfall and plant cover. A match is scored with one transparent formula and fixed tolerances
in real units. Three presets (Balanced, Terrain and mobility, Thermal hardware) reweight the
score for different tests. A search over all of Earth's land takes about 30 milliseconds in a
Web Worker.

**What it found.** For Jezero Crater the closest matches are in the Atacama region of Chile,
the Turpan basin in China, the Tibesti of northern Chad and the deserts of south-east Iran.
For Gale Crater they are the Atacama again and the Dunhuang area of China. Nowhere on Earth
is much like Mars on temperature: Mars targets average about 210 K with a swing of about 80 K
between day and night, so the best Earth cells reach about 70 out of 100. These are candidate
regions for field checks, not discoveries.

**The evidence, including the part that failed.** The engine was never told about 15 famous
analog sites. Our first version scored five measurements and placed only 7%, 5% and 6% of
those sites (one figure per preset) in the best 10% of Earth's land, where chance gives 10%.
It had no way to tell a desert from a rainforest. We tried the one tolerance change our plan
allowed and it did not help. We then added rainfall and plant cover, with thresholds fixed
beforehand (250 mm a year and a vegetation index of 0.2), and ran the test once more: 15%,
17% and 17%. That is above chance by a modest margin, and because the change came after a
failure it is weaker evidence than a test planned in advance. The engine also passes its
internal checks: an Earth cell matched against Earth returns itself with a score of 100,
nudging a target keeps 71% of the top matches in the same regions, and every data reader
puts known landmarks in the right place.

**The limits.** A 30 km cell describes a region, not a crater or a lava tube. Temperature
comes from different kinds of source on each world: a reanalysis on Earth, a climate model on
Mars, a radiometer on the Moon. Lunar south-pole sites fall in the grid's low-confidence
zone. Earth cannot copy low gravity, a thin or absent atmosphere, or the radiation. Every
passport says so.

**How it could help a mission.** As a first filter: given a landing site and a purpose, it
lists dry, bare regions whose slopes, relief and brightness match, and shows plainly how far
each falls short on temperature. The hometown mode turns the same engine into an outreach tool.

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
- [ ] Research the top surprise sites: what is really at 42.4 N, 89.6 E in China (Turpan basin) and 20.9 N, 17.6 E in Chad (Tibesti)
- [ ] Record the 30-second demo: click Jezero Crater, open the passport, then type a hometown
- [ ] Add team members to README.md and this file
- [ ] Test every link in a private browser window
