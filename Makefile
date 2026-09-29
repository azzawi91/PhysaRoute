# PhysaRoute reproduction pipeline.
#   make            install → test → simulate → stats → figures → numbers
#   make quick      3-seed smoke run of every experiment (≈10 min)
PYTHON ?= python3
SEEDS  ?= 30
PROCS  ?= 2

.PHONY: all install test simulate stats figures numbers quick clean

all: install test simulate stats figures numbers

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest -q tests

simulate:
	$(PYTHON) -m physaroute.experiments --exp all --seeds $(SEEDS) --procs $(PROCS)

stats:
	$(PYTHON) -m physaroute.stats

figures:
	$(PYTHON) -m physaroute.plots

numbers:
	$(PYTHON) -m physaroute.report_numbers

quick:
	$(PYTHON) -m physaroute.experiments --exp all --seeds 3 --procs $(PROCS)
	$(PYTHON) -m physaroute.stats && $(PYTHON) -m physaroute.plots && $(PYTHON) -m physaroute.report_numbers

clean:
	rm -rf data/*.csv figures/*.png figures/*.pdf manuscript/shared/numbers.tex
