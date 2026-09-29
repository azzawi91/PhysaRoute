#!/bin/bash
# Full reproduction run (about two hours on two cores); log goes to logs/run_all.log.
cd "$(dirname "$0")"
mkdir -p logs
python3 -m physaroute.experiments --exp all --seeds 30 --procs 2
