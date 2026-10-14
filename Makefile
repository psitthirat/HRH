# Commands of the HRH research tree (Chapters 4-5, service modules, Lab source handoff).
# Run from the repository root. Start with PROJECT_LOG.md for context and timings.
# The presentation website and Workforce Lab live in workspaces/HRH-authoring (separate repository).

PY ?= .venv/bin/python

.PHONY: help test
help:
	@echo "Chapter 4 (situation analysis)"
	@echo "  make chapter4            shared data, notebooks 4.1-4.6 and the Thai report (~3 min with cache)"
	@echo "  make chapter4-report     re-render the Thai report from the current claims (seconds)"
	@echo "Chapter 5 (15-year physician allocation)"
	@echo "  make chapter5            inputs, plans, uncertainty, comparison, report (~70 min; run detached)"
	@echo "  make chapter5-compare    comparison stage only (reuses the plan cache)"
	@echo "  make chapter5-report     re-render the Thai report from the current claims (seconds)"
	@echo "  make chapter5-notebooks  execute the chapter 5 notebooks against the current outputs"
	@echo "Service modules and the Lab handoff"
	@echo "  make services-population export the service-module population denominator"
	@echo "  make sync-lab-check      list differences with workspaces/HRH-authoring"
	@echo "  make sync-lab-source     copy the canonical scientific source to the authoring workspace"
	@echo "Tests"
	@echo "  make test                all tests of src/ (tests/)"

test:
	PYTHONPATH=src $(PY) -m pytest tests -q

## ---------------------------------------------------------------- Chapter 4 (unified pipeline)
.PHONY: chapter4 chapter4-shared chapter4-report chapter4-test
chapter4:            ## shared data, notebooks 4.1-4.6 and the Thai report
	PYTHONPATH=src $(PY) -m chapter4.build --all
chapter4-shared:
	PYTHONPATH=src $(PY) -m chapter4.build --shared
chapter4-report:
	PYTHONPATH=src $(PY) -m chapter4.build --report
chapter4-test:
	$(PY) -m pytest tests/test_chapter4_metrics.py -q

## ---------------------------------------------------------------- Chapter 5 (15-year physician allocation)
# Any change to src/chapter4/*.py, config/analysis.toml, config/source_registry.toml or
# config/chapter5.toml invalidates the plan cache (full ~70 min rebuild).
# Override any knob without editing the config:  make chapter5 SET="supply.annual_path=2500" NAME=pool2500
.PHONY: chapter5 chapter5-inputs chapter5-plans chapter5-uncertainty chapter5-compare chapter5-report \
        chapter5-notebooks chapter5-test
C5 = PYTHONPATH=src $(PY) -m chapter5.build $(foreach s,$(SET),--set $(s)) $(if $(NAME),--name $(NAME),)
chapter5:             ## inputs, plans, uncertainty, comparison, figures, workbook, Thai report
	$(C5) --all
chapter5-inputs:
	$(C5) --inputs
chapter5-plans:
	$(C5) --plans
chapter5-uncertainty:
	$(C5) --uncertainty
chapter5-compare:
	$(C5) --compare
chapter5-report:
	$(C5) --report
chapter5-notebooks:   ## execute the chapter 5 notebooks (after `make chapter5`)
	$(C5) --notebooks
chapter5-test:
	PYTHONPATH=src $(PY) -m pytest tests/test_chapter5.py -q

## ---------------------------------------------------------------- service modules and the Lab handoff
# The research tree owns src/chapter4, src/chapter5, src/services and the analysis configs; the authoring
# workspace receives byte-identical copies with a SHA-256 manifest (scripts/sync_scientific_source.py).
.PHONY: sync-lab-check sync-lab-source services-population
services-population: ## export the service-module population denominator (age groups + women) for the Lab
	PYTHONPATH=src $(PY) -m services.lab_modules --export-population outputs/services/service_population.json
sync-lab-check:      ## list differences between the research tree and workspaces/HRH-authoring
	$(PY) scripts/sync_scientific_source.py --check
sync-lab-source:     ## copy the canonical scientific source into the authoring workspace (refuses to drop edits)
	$(PY) scripts/sync_scientific_source.py --apply
