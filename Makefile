# =============================================================================
# PhysaRoute — top-level Makefile
# =============================================================================
# One-command reproduction pipeline.
#
#   make            — install Python deps, run simulator, build paper
#   make simulate   — only run the simulator (figures + CSV data)
#   make figures    — alias for `simulate`
#   make paper      — only build the docx manuscript
#   make latex      — build the IEEE LaTeX PDF (requires TeX Live + IEEEtran)
#   make clean      — wipe figures/, data/, and LaTeX intermediates
#
# Requires:
#   - Python 3.10+
#   - Node 18+   (for the docx build pipeline)
#   - pdflatex + bibtex + IEEEtran  (for `make latex`)
# =============================================================================

PYTHON ?= python3
NODE   ?= node
NPM    ?= npm

.PHONY: all install simulate figures paper latex clean help

all: install simulate paper

help:
	@echo "PhysaRoute build targets:"
	@echo "  make            — install + simulate + paper"
	@echo "  make install    — install Python and Node dependencies"
	@echo "  make simulate   — run the simulator, generate figures + data"
	@echo "  make paper      — build the .docx manuscript"
	@echo "  make latex      — build the .pdf manuscript via IEEEtran"
	@echo "  make clean      — wipe generated artefacts"

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(NPM) install

simulate figures:
	$(PYTHON) src/physaroute_sim.py

paper:
	$(NODE) manuscript/build_paper.js

latex:
	cd latex && pdflatex PhysaRoute_IEEE_IoTJ_Template
	cd latex && bibtex   PhysaRoute_IEEE_IoTJ_Template
	cd latex && pdflatex PhysaRoute_IEEE_IoTJ_Template
	cd latex && pdflatex PhysaRoute_IEEE_IoTJ_Template

clean:
	rm -rf figures/* data/*
	rm -f latex/*.aux latex/*.log latex/*.bbl latex/*.blg \
	      latex/*.out latex/*.toc latex/*.synctex.gz
	rm -f *.docx
