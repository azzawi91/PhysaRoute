# =============================================================================
# PhysaRoute — experiment-reproduction Makefile.
#
# This Makefile is the single command-line entry point promised in the
# manuscript's data-availability statement.  Running `make` from a clean
# clone reproduces every figure and table from the master seed 20260425.
#
#   make            — install dependencies → calibrate → simulate → figures
#   make install    — pip install -r requirements.txt
#   make calibrate  — run src/calibrate_channel.py (writes data/calibration.csv)
#   make simulate   — run src/physaroute_sim_v2.py (writes data/*.csv)
#   make figures    — run src/plot_figures.py (writes figures/*.png)
#   make clean      — wipe data/ and figures/
#
# Requirements: Python 3.10 or newer.
# =============================================================================

PYTHON ?= python3

.PHONY: all install calibrate simulate figures clean help

all: install calibrate simulate figures

help:
	@echo "PhysaRoute build targets:"
	@echo "  make            — install + calibrate + simulate + figures"
	@echo "  make install    — install Python dependencies"
	@echo "  make calibrate  — run channel-shadowing calibration"
	@echo "  make simulate   — run the simulator"
	@echo "  make figures    — render figures from CSVs"
	@echo "  make clean      — wipe data/ and figures/"

install:
	$(PYTHON) -m pip install -r requirements.txt

calibrate:
	$(PYTHON) src/calibrate_channel.py

simulate:
	$(PYTHON) src/physaroute_sim_v2.py

figures:
	$(PYTHON) src/plot_figures.py

clean:
	rm -rf figures/* data/*
