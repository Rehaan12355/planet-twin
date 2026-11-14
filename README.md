# Planet Twin

Find the place on Earth most like any spot on Mars or the Moon, and see where the likeness ends.

**Live site:** https://rehaan12355.github.io/planet-twin/

**Challenge:** NASA Space Apps Challenge 2026, *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*

**Team:** Rehaan Irfan (more names to be added)

## What it does

Click a point on a Mars or Moon globe. A pin drops, and an Earth globe spins to the closest
match among 342,571 land cells. An analog passport shows each measurement on both worlds in
real units, where the analogy breaks, and what a mission could test there.

- **Three worlds, one grid.** Every world is cut into cells about 30 km wide, each with the same
  seven measurements: mean slope, local relief, mean surface temperature, day-night temperature
  range, albedo, yearly rainfall and plant cover.
- **One transparent score.** Closeness is judged with fixed tolerances in real units. Nothing is
  trained. All matching runs in your browser in about 30 ms.
- **Three purposes.** Balanced, Terrain and mobility, and Thermal hardware presets, plus sliders.
- **Honest by design.** Every passport lists what Earth cannot copy: gravity, air and radiation.
- **Hometown twin.** Type a city and fly to its twin on Mars. This is a relative match, labelled as such.

## What we found

- For Jezero Crater, the closest matches are in the Atacama region of Chile, the Turpan basin
  in China, the Tibesti of northern Chad and the deserts of south-east Iran. For Gale Crater
  they are the Atacama again and the Dunhuang area of China.
- Nowhere on Earth is much like Mars on temperature. Typical Mars targets average about 210 K
  with a swing of about 80 K between day and night, so the best Earth cells reach about 70 out
  of 100: terrain, albedo, dryness and bare ground match, and both temperature rows score zero.
  With the Thermal hardware preset and ice allowed, the closest matches are in Antarctica.
- **The first blind test failed, and we report it.** The engine was never told about 15 famous
  analog sites. The first version scored five measurements and placed 7% (Balanced), 5%
  (Terrain and mobility) and 6% (Thermal hardware) of them in the best 10% of Earth's land.
  Chance gives 10%.
- **After adding rainfall and plant cover, it is above chance by a modest margin:** 15%, 17%
  and 17%. That change was made after seeing the failure, with thresholds fixed beforehand and
  a single re-run, so it is weaker evidence than a test planned in advance. Both results are
  on the [validation page](https://rehaan12355.github.io/planet-twin/validation.html).
- A match from this tool is a candidate region for field checks, not a discovery.

## How it works

A Python pipeline runs once on a laptop and writes small binary files. A static web app loads
them and does all the matching in a Web Worker. Nothing runs on a server.

```
pipeline/sources.py         every dataset: address, access check, download
pipeline/readers/           one reader per dataset, each tested against a landmark
pipeline/terrain.py         slope with the cosine-of-latitude correction, relief
pipeline/build_features.py  writes web/public/data/<world>.bin and .meta.json
pipeline/validate.py        blind test, self-match, stability; writes validation.json
web/src/                    globes, search worker, passport, presets
docs/methods.md             the science in plain words (also the site's Methods page)
```

## How to run

You need Python 3.11 or newer, Node.js 20 or newer and `curl`.

```sh
make test   # pipeline tests
make web    # local site at http://localhost:5173 (the built data files are in the repo)
make build  # static site into web/dist
make data   # optional: download 7 GB of source data and rebuild everything
```

## Data

Twelve of the fifteen datasets are NASA's: MOLA, TES, LOLA, Diviner, MERRA-2 and CERES (through
NASA POWER), MODIS NDVI, the NASA Ames Mars climate model, and the three globe textures. The
others are ETOPO 2022 from NOAA and two Natural Earth layers. Every address, size, date and
licence is in [DATA_SOURCES.md](DATA_SOURCES.md), and the method and its limits are in
[docs/methods.md](docs/methods.md).

NASA retired its Earth Observations (NEO) archive in September 2026. This project's plan
relied on it, so Earth's temperature and albedo come from NASA POWER instead.

## AI use

Most of the code in this repository was written with AI assistance (Claude, through Claude
Code). See [AI_USE.md](AI_USE.md). The app contains no AI-generated images, video or audio.

## Licence

MIT. Data remains under the terms of its providers, listed in DATA_SOURCES.md.
