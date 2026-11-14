# Data sources

Every dataset used by Planet Twin. This file is written by `python -m pipeline.sources docs`
from `pipeline/sources.py` and the download manifest (`data/raw/manifest.json`, which also holds
a SHA-256 checksum for every file). Total download: 7.05 GB in 184 files.

## NASA data

| Dataset | World | Used for | Provider | Files | Size | Downloaded | Licence |
|---|---|---|---|---|---|---|---|
| [NASA POWER v10 climatology of MERRA-2 (0.5 x 0.625 degree)](https://power.larc.nasa.gov) | Earth | Mean surface temperature, day-night range, rainfall, snow cover | NASA LaRC POWER / NASA GMAO MERRA-2 | 1 | 54.1 MB | 2026-11-14 | NASA open data (CC0-style, see POWER LICENSE.txt) |
| [NASA POWER v10 climatology of CERES SYN1deg (1 degree)](https://power.larc.nasa.gov) | Earth | Albedo | NASA LaRC POWER / NASA CERES | 1 | 3.4 MB | 2026-11-14 | NASA open data (see POWER LICENSE.txt) |
| [MODIS/Terra MOD13C2 monthly NDVI, 0.1 degree (NEO float GeoTIFF)](https://science.nasa.gov/earth/nasa-earth-observations-neo/) | Earth | Barren-land filter, passport | NASA (MODIS, via NASA Earth Observations) | 12 | 74.3 MB | 2026-11-14 | NASA open data |
| [Blue Marble: Shaded Relief and Bathymetry (NASA GIBS)](https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api) | Earth | Globe texture (display only) | NASA GIBS / NASA Earth Observatory | 1 | 0.9 MB | 2026-11-14 | NASA open data |
| [MGS MOLA MEGDR topography, 16 pixels per degree (megt90n000eb)](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | Mars | Slope, relief | NASA PDS Geosciences Node | 2 | 33.2 MB | 2026-11-14 | Public domain (NASA PDS) |
| [MGS TES bolometric albedo global mosaic, 7.4 km](https://astrogeology.usgs.gov/search/map/mars_mgs_tes_albedo_global_mosaic_7410m) | Mars | Albedo | USGS Astrogeology / NASA MGS TES | 1 | 16.6 MB | 2026-11-14 | Public domain |
| [NASA Ames Legacy Mars Global Climate Model reference simulation (active clouds), 5 x 6 degree](https://data.nas.nasa.gov/mcmcref/legacygcm/) | Mars | Mean surface temperature, day-night range | NASA Ames Mars Climate Modeling Center | 12 | 3.52 GB | 2026-11-14 | Public domain (NASA) |
| [Viking MDIM 2.1 colour mosaic (NASA Solar System Treks tiles)](https://trek.nasa.gov/mars/) | Mars | Globe texture (display only) | NASA Solar System Treks / USGS Astrogeology | 128 | 6.8 MB | 2026-11-14 | Public domain |
| [LRO LOLA gridded elevation, 16 pixels per degree (LDEM_16)](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) | Moon | Slope, relief | NASA PDS Geosciences Node | 2 | 33.2 MB | 2026-11-14 | Public domain (NASA PDS) |
| [LRO Diviner Global Cumulative Products, 0.5 degree by local time](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm) | Moon | Mean surface temperature, day-night range | NASA PDS Geosciences Node (UCLA Diviner team) | 18 | 2.81 GB | 2026-11-14 | Public domain (NASA PDS) |
| [LRO LOLA 1064 nm normal albedo, 4 pixels per degree (LDAM_4)](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) | Moon | Albedo | NASA PDS Geosciences Node | 2 | 4.2 MB | 2026-11-14 | Public domain (NASA PDS) |
| [LROC WAC colour map (NASA SVS CGI Moon Kit), 4k](https://svs.gsfc.nasa.gov/4720) | Moon | Globe texture (display only) | NASA Scientific Visualization Studio | 1 | 13.1 MB | 2026-11-14 | Public domain (NASA) |

## Other data

| Dataset | World | Used for | Provider | Files | Size | Downloaded | Licence |
|---|---|---|---|---|---|---|---|
| [ETOPO 2022 global relief, 60 arc-second, surface elevation](https://www.ncei.noaa.gov/products/etopo-global-relief-model) | Earth | Slope, relief | NOAA NCEI | 1 | 478.3 MB | 2026-11-14 | Public domain (US Government) |
| [Natural Earth 1:50m land polygons](https://www.naturalearthdata.com) | Earth | Land mask | Natural Earth | 1 | 0.5 MB | 2026-11-14 | Public domain |
| [Natural Earth 1:10m populated places](https://www.naturalearthdata.com) | Earth | Hometown search | Natural Earth | 1 | 0.7 MB | 2026-11-14 | Public domain |

## Changes from the original plan, and why

- **NASA POWER v10 climatology of MERRA-2 (0.5 x 0.625 degree):** Replaces the MODIS NEO archive, which NASA decommissioned in September 2026.
- **NASA POWER v10 climatology of CERES SYN1deg (1 degree):** Replaces MODIS albedo from the decommissioned NEO archive.
- **MODIS/Terra MOD13C2 monthly NDVI, 0.1 degree (NEO float GeoTIFF):** NEO was decommissioned in September 2026. These are Internet Archive copies of the original NASA files, one per calendar month.
- **NASA Ames Legacy Mars Global Climate Model reference simulation (active clouds), 5 x 6 degree:** Model output, not an observation. Chosen over OpenMARS (CC BY-NC-ND, which does not allow sharing derived maps). 12 of 67 ten-sol files, evenly spaced over the Mars year.
- **LRO LOLA 1064 nm normal albedo, 4 pixels per degree (LDAM_4):** Normal albedo at one laser wavelength (1064 nm), not broadband. Stated on the methods page.
- **Earth temperature, albedo, rainfall and snow** were planned from MODIS and IMERG layers in the NASA Earth
  Observations (NEO) archive. NASA decommissioned NEO in September 2026 and its archive now redirects to a
  notice page. The replacement is NASA POWER, which serves NASA's MERRA-2 reanalysis and CERES products with
  no login. These grids are coarser (about 55 km for temperature, 110 km for albedo) than the 30 km cells.
- **No dataset needed an Earthdata login**, and none was worked around.

## Download addresses

- `earth_elevation`: https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc
- `earth_merra2`: https://nasa-power.s3.us-west-2.amazonaws.com/merra2/temporal/power_merra2_climatology_temporal_utc.zarr
- `earth_ceres`: https://nasa-power.s3.us-west-2.amazonaws.com/syn1deg/temporal/power_syn1deg_climatology_temporal_utc.zarr
- `earth_ndvi`: https://web.archive.org/web/20250416221001id_/https://neo.gsfc.nasa.gov/archive/geotiff.float/MOD_NDVI_M/MOD13C2.A2023001.061.2023034191717.tif (first of 12 files; full list in `pipeline/sources.py`)
- `earth_land`: https://naciscdn.org/naturalearth/50m/physical/ne_50m_land.zip
- `earth_places`: https://naciscdn.org/naturalearth/10m/cultural/ne_10m_populated_places_simple.zip
- `earth_texture`: https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&LAYERS=BlueMarble_ShadedRelief_Bathymetry&STYLES=&FORMAT=image/jpeg&CRS=EPSG:4326&BBOX=-90,-180,90,180&WIDTH=4096&HEIGHT=2048
- `mars_elevation`: https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/megt90n000eb.img (first of 2 files; full list in `pipeline/sources.py`)
- `mars_albedo`: https://planetarymaps.usgs.gov/mosaic/Mars_MGS_TES_Albedo_mosaic_global_7410m.tif
- `mars_temperature`: https://data.nas.nasa.gov/legacygcm/legacygcm/ACTIVECLDS_NCDF/LegacyGCM_Ls000_Ls004.nc (first of 12 files; full list in `pipeline/sources.py`)
- `mars_texture`: https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/3/0/0.jpg (first of 128 files; full list in `pipeline/sources.py`)
- `moon_elevation`: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.img (first of 2 files; full list in `pipeline/sources.py`)
- `moon_temperature`: https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/global_cumul_avg_cyl_90s80s_002.tab (first of 18 files; full list in `pipeline/sources.py`)
- `moon_albedo`: https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/float_img/ldam_4_float.img (first of 2 files; full list in `pipeline/sources.py`)
- `moon_texture`: https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_poles_4k.tif
