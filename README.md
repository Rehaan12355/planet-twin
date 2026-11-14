# Planet Twin

Find the place on Earth most like any spot on Mars or the Moon, and see why.

**Challenge:** NASA Space Apps Challenge 2026 — *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*

**Team:** Rehaan Irfan (more names to be added)

## What it does

Click a point on a Mars or Moon globe. A pin drops, and an Earth globe spins to the
closest match. An analog passport shows each measurement on both worlds in real units,
where the analogy breaks, and what a mission could test there.

## How to run

```sh
make test   # run pipeline tests
make data   # download and build feature files (needs data sources, see DATA_SOURCES.md)
make web    # start the local web app
make build  # build the static site into web/dist
```

## AI use

The code in this repository was written with AI assistance (Claude, via Claude Code).
See [AI_USE.md](AI_USE.md).
