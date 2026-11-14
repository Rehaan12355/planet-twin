# How Planet Twin works

Planet Twin finds the place on Earth most like any spot on Mars or the Moon, and shows why.
This page explains the method in plain words, including where it falls short.

## The idea in one paragraph

Every world is cut into cells about 30 km wide. Each cell gets the same five measurements.
A match is the Earth land cell whose measurements are closest to the target cell's, judged
with fixed tolerances in real units. Nothing is trained and nothing is hidden: you can check
every number on the passport against its source.

## The grid

Cells have nearly the same ground size on all three worlds, so a cell on Mars compares fairly
with a cell on Earth.

| World | Radius (km) | Cell size (degrees) | Grid (columns x rows) | Cell width at the equator (km) |
|---|---|---|---|---|
| Earth | 6371.0 | 0.25 | 1440 x 720 | 27.8 |
| Mars | 3389.5 | 0.5 | 720 x 360 | 29.6 |
| Moon | 1737.4 | 1.0 | 360 x 180 | 30.3 |

Only Earth's land cells are searched: 342,571 of them. A cell counts as land when at least
half of it is land in the Natural Earth 1:50m map.

## The five measurements

| Measurement | Unit | How it is computed | Tolerance |
|---|---|---|---|
| Mean slope | degrees | Slope on a grid of about 3.7 km, averaged over the cell | 2 |
| Local relief | log10 of metres | Highest minus lowest elevation in the cell | 0.25 |
| Mean surface temperature | kelvin | Average surface temperature over a year, day and night | 15 |
| Day-night temperature range | kelvin | Warmest minus coldest time of day, averaged over a year | 15 |
| Albedo | 0 to 1 | Share of sunlight the ground reflects | 0.05 |

Slope is measured at the same ground scale everywhere: 2 arc-minutes on Earth, 16 pixels per
degree on Mars and 8 pixels per degree on the Moon, all close to 3.7 km. On a latitude-longitude
grid the east-west pixel shrinks towards the poles, so its size is scaled by the cosine of
latitude. Ocean pixels are set to sea level before Earth's slopes are computed, so a coastal
cell is not scored on the sea floor.

Relief is shown on the passport in metres. It is scored on a log scale because the difference
between 50 m and 500 m matters more than the difference between 3000 m and 3450 m.

## The score

For each measurement, closeness is a number from 0 to 1:

```
match = exp(-0.5 * ((earth value - target value) / tolerance)^2)
score = 100 * sum(weight * match) / sum(weight)
```

A difference of one tolerance gives a match of 0.61; two tolerances give 0.14. The overall
score is the weighted average, from 0 to 100. If a measurement is missing for a cell, it is
left out of the average and the passport says so. It is never counted as zero.

Three presets set the weights, and sliders allow any other mix.

| Preset | Terrain | Temperature | Albedo |
|---|---|---|---|
| Balanced | 1 | 1 | 1 |
| Terrain and mobility | 3 | 0.5 | 0.5 |
| Thermal hardware | 0.5 | 3 | 1 |

The five best matches are kept at least 300 km apart, so the results are five places and not
five neighbouring cells.

## Two ways to compare

**Physical match** is the default. It compares real values. If nowhere on Earth is as cold as
a lunar crater, the temperature row scores zero and the passport says so.

**Relative match** is used only for the hometown twin. It compares where each value ranks
within its own world, with a tolerance of 10 percentile points. Your town's twin on Mars is
the place that is as steep, as warm and as bright *for Mars* as your town is *for Earth*.
It is labelled as relative everywhere it appears, because your town is not physically like Mars.

## Where the numbers come from

| Measurement | Earth | Mars | Moon |
|---|---|---|---|
| Slope, relief | ETOPO 2022 (NOAA) | MOLA topography (NASA) | LOLA topography (NASA) |
| Temperature | MERRA-2 skin temperature, through NASA POWER | NASA Ames Legacy Mars climate model | Diviner radiometer (NASA) |
| Albedo | CERES surface albedo, through NASA POWER | TES bolometric albedo (NASA, USGS) | LOLA 1064 nm albedo (NASA) |

Rainfall, snow cover (MERRA-2) and the vegetation index (MODIS NDVI) are shown on Earth's
passports as context. They are not part of the score. Full addresses, sizes, dates and licences
are in [DATA_SOURCES.md](https://github.com/Rehaan12355/planet-twin/blob/main/DATA_SOURCES.md).

## What changed from the plan

NASA retired its Earth Observations (NEO) site in September 2026, two months before this
hackathon. The plan relied on NEO for MODIS temperature and albedo, so Earth's temperature and
albedo now come from NASA's MERRA-2 and CERES products instead. Mars temperature comes from the
NASA Ames model rather than the OpenMARS reanalysis, because the OpenMARS licence does not
allow sharing maps derived from it.

## Limits you should know about

**The three worlds were not measured the same way.** This is the weakest point of the method.

- *Temperature.* Earth's is a weather reanalysis on a grid of about 55 km. The Moon's is a
  direct satellite measurement. Mars's is a climate model on a 5 by 6 degree grid, about 300 km,
  sampled on 120 Martian days spread over one year. The Mars map is therefore smooth: a crater
  floor and its rim get nearly the same temperature. The model is run for a typical year and
  is not a record of any real year.
- *Day-night range.* On Earth this is the average daily maximum minus the average daily
  minimum of hourly skin temperature. On Mars it is the warmest minus the coldest of 16 times of
  day. On the Moon it is the warmest minus the coldest hour of the lunar day, which lasts about
  29.5 Earth days. Each is that world's own day.
- *Albedo.* Earth's is all-sky surface albedo across the solar spectrum, at about 110 km, and
  it includes snow and seasonal plants. Mars's is bolometric albedo from TES. The Moon's is
  reflectance at one laser wavelength (1064 nm), which is not the same as broadband albedo.
  Treat the albedo row for the Moon as a guide.

**Scale.** A 30 km cell describes a region. It cannot confirm a specific crater, cave or lava
tube. Coarser inputs (temperature, albedo) are interpolated to the cells and do not gain detail
by it.

**The poles.** Cells within 5 degrees of a pole are marked low confidence. The grid stretches
there, slopes are less reliable, and the lunar south-pole sites that matter most for a Moon
base sit in exactly that zone. Permanently shadowed craters are far smaller than a cell.

**What Earth cannot copy.** Gravity (9.81 m/s² against 3.71 on Mars and 1.62 on the Moon), air
pressure (about 1,013 hPa against about 6 hPa on Mars and a vacuum on the Moon) and radiation.
Natural background on Earth averages about 2.4 mSv a year (UNSCEAR). Curiosity's RAD instrument
measured about 0.67 mSv a day on the surface of Mars (Hassler and others, 2014) and Chang'e 4
measured about 1.4 mSv a day on the Moon (Zhang and others, 2020). Every passport lists these.

**Mars is cold.** With temperature in the score, the closest matches to most of Mars are ice
sheets and high cold deserts. That is a real finding. The "Hide ice and snow" switch removes
cells that are snow-covered for half the year or more, and it is on by default so that the
results include places people can work in. Turn it off to see the unfiltered answer.

**A match is a candidate, not a discovery.** The engine has never seen the rocks, the dust or
the water chemistry. Any site it suggests needs a field check.

## How we tested it

See the [validation page](./validation.html) for the full numbers. In short:

- **Blind test on famous analog sites: the engine does not find them.** It was never told about
  the Atacama, Devon Island, Death Valley and twelve other sites scientists already use. Across
  ten Mars targets, 7% of those sites land in the best 10% of Earth's land with the Balanced
  preset, 5% with Terrain and mobility and 6% with Thermal hardware. Chance would give 10%.
  The reason is on the validation page: Mars is so much colder than those sites that
  temperature scores near zero for almost all of Earth, and slope, relief and albedo alone do
  not single out a famous desert. The sites were chosen for minerals, chemistry and access,
  which this engine cannot see.
- **Stability: partly.** When a Mars target is moved by one cell, 54% of the top-five matches
  stay within 600 km of an original match. Many Earth cells tie at nearly the same score, so
  the top five can jump between look-alike regions. The heat layer shows the whole field of
  candidates and is the better guide.
- **Self-match: passed.** An Earth cell searched against Earth returns itself with a score of
  100, in 200 of 200 random trials.
- **Reader checks: passed.** Each data reader puts known landmarks in the right place:
  Olympus Mons is among the highest cells on Mars, a Himalaya cell has over 3000 m of relief,
  the central Sahara is flat and brighter than the Amazon, Mars is colder at its poles, and
  the lunar equator swings by 296 K between day and night.

The plan allowed the tolerances to be revisited once after the blind test. We tried doubling
the two temperature tolerances from 15 K to 30 K, because at 15 K they score near zero for
about 80% of Earth's land against any Mars target. The blind-test numbers became 8%, 5% and
3%, which is no better, so the original tolerances were kept.

## What this means for using Planet Twin

Use it to shortlist regions whose terrain and brightness match a target, and to see at a glance
how far every place on Earth falls short on temperature. Do not use a high rank as proof that
a place is a good analog. The engine cannot see geology, chemistry or dust, and it did not
rediscover the sites that experts picked for those reasons.
