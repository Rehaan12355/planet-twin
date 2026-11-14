VENV := .venv
PY := $(VENV)/bin/python

.PHONY: venv data test web build

$(VENV)/bin/activate: pipeline/requirements.txt
	python3 -m venv $(VENV)
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q --prefer-binary -r pipeline/requirements.txt
	touch $(VENV)/bin/activate

venv: $(VENV)/bin/activate

data: venv
	$(PY) -m pipeline.build_features

test: venv
	$(PY) -m pytest -q pipeline/tests

web:
	cd web && npm install && npm run dev

build:
	cd web && npm ci && npm run build
