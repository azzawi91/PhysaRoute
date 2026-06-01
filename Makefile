# =============================================================================
# PhysaRoute — top-level Makefile
# =============================================================================
# One-command reproduction pipeline.
#
#   make            — install Python deps and run the simulator
#   make simulate   — only run the simulator (figures + CSV data)
#   make figures    — alias for `simulate`
#   make install    — install Python dependencies
#   make clean      — wipe figures/ and data/
#
# Requires:
#   - Python 3.10+
# =============================================================================

PYTHON ?= python3

.PHONY: all install simulate figures clean help

all: install simulate

help:
	@echo "PhysaRoute build targets:"
	@echo "  make            — install + simulate"
	@echo "  make install    — install Python dependencies"
	@echo "  make simulate   — run the simulator, generate figures + data"
	@echo "  make clean      — wipe generated artefacts"

install:
	$(PYTHON) -m pip install -r requirements.txt

simulate figures:
	$(PYTHON) src/physaroute_sim.py

clean:
	rm -rf figures/* data/*
