# Commands for the interactive research report.
#
# Every target below is a real command in this repository. The analysis
# pipeline is deliberately NOT wired into `web-data`: rebuilding prose or
# styling must never trigger model estimation.

PY      ?= .venv/bin/python
SITE    ?= site
OUT     ?= chapter4_outputs
PORT    ?= 8765

.PHONY: help web-data web-serve web-test web-release web-offline web-check \
        web-clean analysis

help:
	@echo "Interactive research report"
	@echo "  make web-data      rebuild the website data bundle from the analysis exports"
	@echo "  make web-serve     serve the site locally at http://127.0.0.1:$(PORT)"
	@echo "  make web-test      run the acceptance tests (synthetic fixtures only)"
	@echo "  make web-release   validate strictly and promote a release snapshot"
	@echo "  make web-offline   assemble a self-contained meeting bundle"
	@echo "  make web-check     data bundle + tests, the pre-commit gate"
	@echo "  make web-clean     remove generated site data (keeps approvals.json)"
	@echo ""
	@echo "  make analysis      re-run the upstream analysis (slow; rarely needed)"
	@echo ""
	@echo "Research-project storytelling website (story/; reads the analysis outputs in outputs/chapter4_*)"
	@echo "  make story-data    build a draft release     make story-check   validate only"
	@echo "  make story-serve   serve at :8780            make story-test    exporter tests"
	@echo "  make story-copy    list where every text lives (docs/web_story/copy_index.md)"
	@echo "  make story-release RELEASE=<id> REVIEWER=... promote   make story-offline  meeting copy"
	@echo "  make story-setup   install website dependencies in .venv"
	@echo "  make story-public  sanitized public website (slides, exploration, appendix; no speaker notes)"
	@echo "  make story-public-repo  update the separate public Git workspace"
	@echo "  make story-handoff      assemble the private authoring workspace"

## Rebuild the bundle. Reads the exports; never writes to them.
web-data:
	$(PY) -m scripts.webexport.build --indir $(OUT) --outdir $(SITE)/data

## Serve locally. A plain static server is enough: there is no build step.
web-serve:
	@echo "Serving $(SITE) at http://127.0.0.1:$(PORT)  (Ctrl-C to stop)"
	@cd $(SITE) && $(abspath $(PY)) -m http.server $(PORT) --bind 127.0.0.1

web-test:
	$(PY) -m pytest tests -q

## A release build is strict: it fails on any validation problem, including a
## scientific interpretation whose dependencies have changed since approval.
web-release:
	$(PY) -m scripts.webexport.build --indir $(OUT) --outdir $(SITE)/data
	@$(PY) scripts/webexport/release.py promote

## Offline meeting bundle: the site plus one pinned release, no network.
web-offline:
	$(PY) scripts/webexport/release.py offline --port $(PORT)

web-check: web-data web-test
	@echo "bundle rebuilt and acceptance tests passed"

web-clean:
	rm -rf $(SITE)/data/releases $(SITE)/data/releases.json $(SITE)/data/review_queue.json
	@echo "removed generated release data (approvals.json kept)"

## The upstream analysis. Slow, and not a dependency of the website build.
analysis:
	$(PY) scripts/build_ch4_analysis.py
	$(PY) scripts/build_ch4_handover.py
	$(PY) scripts/ch4_rebuild.py
	$(PY) scripts/ch4_rebuild_figures.py
	$(PY) scripts/ch4_universe_dictionary.py
	$(PY) scripts/ch4_rebuild_workbook.py
	$(PY) scripts/ch4_manuscript.py
	$(PY) scripts/ch4_qc.py

## ---------------------------------------------------------------- Chapter 4 (unified pipeline)
.PHONY: chapter4 chapter4-shared chapter4-report chapter4-test
chapter4:            ## shared data, the four notebooks, and the Thai report
	PYTHONPATH=src $(PY) -m chapter4.build --all
chapter4-shared:
	PYTHONPATH=src $(PY) -m chapter4.build --shared
chapter4-report:
	PYTHONPATH=src $(PY) -m chapter4.build --report
chapter4-test:
	$(PY) -m pytest tests/test_chapter4_metrics.py -q

## ---------------------------------------------------------------- storytelling website (story/)
# Story / presentation / explore site of the research project, built from outputs/chapter4_*
# (the unified analysis pipeline keeps its historical package name). Runbook: docs/web_story/update_runbook.md
.PHONY: story-data story-check story-test story-browser-test story-serve story-list story-release \
        story-offline story-prune story-screens story-copy
STORY_PORT ?= 8780

story-data:          ## build a draft release (outputs/web/<id>/, story/data/releases/<id>/)
	$(PY) -m scripts.webstory.build
story-check:         ## build in memory and validate; writes nothing; exit 1 on errors
	$(PY) -m scripts.webstory.build --check
story-test:          ## exporter tests on copied fixtures (never touches research data)
	$(PY) -m pytest tests/test_web_story.py -q
story-browser-test:  ## real-browser checks; needs `make story-serve` in another shell
	STORY_URL=http://127.0.0.1:$(STORY_PORT) $(PY) -m pytest tests/test_story_browser.py -q
story-serve:         ## static server for story/ (no build step)
	@echo "Serving story/ at http://127.0.0.1:$(STORY_PORT)  (Ctrl-C to stop)"
	@cd story && $(abspath $(PY)) -m http.server $(STORY_PORT) --bind 127.0.0.1
story-list:
	$(PY) -m scripts.webstory.release list
story-copy:          ## where every text on the site lives (file:line) -> docs/web_story/copy_index.md
	$(PY) -m scripts.webstory.copyindex
story-release:       ## promote: make story-release RELEASE=<id> REVIEWER="ชื่อผู้ทบทวน"
	$(PY) -m scripts.webstory.release promote $(RELEASE) $(if $(REVIEWER),--reviewed-by "$(REVIEWER)",)
story-offline:       ## self-contained meeting copy of one release: make story-offline [RELEASE=<id>]
	$(PY) -m scripts.webstory.release offline $(RELEASE)
story-prune:         ## delete old draft releases (keeps current, latest and 3 drafts)
	$(PY) -m scripts.webstory.release prune --keep 3
story-screens:       ## refresh docs/web_story/screens/ (needs story-serve)
	STORY_URL=http://127.0.0.1:$(STORY_PORT) STORY_SCREENS=1 $(PY) -m pytest tests/test_story_browser.py -q -k screens

## Public deployment and private authoring are different packages. No target
## below pushes to GitHub or re-runs the research analysis.
.PHONY: story-setup story-public story-public-repo story-handoff story-public-test
STORY_PUBLIC_OUT ?= dist/story-public
PUBLIC_REPO ?= workspaces/HRH-slides
STORY_AUTHORING_OUT ?= dist/story-authoring
story-setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements/story-dev.txt
story-public:
	$(PY) -m scripts.webstory.publish $(if $(RELEASE),--release "$(RELEASE)",) --out "$(STORY_PUBLIC_OUT)"
story-public-repo: story-public
	$(PY) -m scripts.webstory.public_repo --artifact "$(STORY_PUBLIC_OUT)" --out "$(PUBLIC_REPO)"
story-handoff:
	$(PY) -m scripts.webstory.handoff $(if $(RELEASE),--release "$(RELEASE)",) --out "$(STORY_AUTHORING_OUT)"
story-public-test:
	$(PY) -m pytest tests/test_publication.py -q

## ---------------------------------------------------------------- Chapter 5 (15-year physician allocation)
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
chapter5-notebooks:   ## execute the three chapter 5 notebooks (after `make chapter5`)
	$(C5) --notebooks
chapter5-test:
	PYTHONPATH=src $(PY) -m pytest tests/test_chapter5.py -q

## ---------------------------------------------------------------- scientific source handoff (Phase 0)
# The research tree owns src/chapter4, src/chapter5 and the analysis configs; the authoring workspace
# receives byte-identical copies with a SHA-256 manifest. Decision: docs/phase0_reconciliation_map.md
.PHONY: sync-lab-check sync-lab-source services-population
services-population: ## export the service-module population denominator (age groups + women) for the Lab
	PYTHONPATH=src $(PY) -m services.lab_modules --export-population outputs/services/service_population.json
sync-lab-check:      ## list differences between the research tree and workspaces/HRH-authoring
	$(PY) scripts/sync_scientific_source.py --check
sync-lab-source:     ## copy the canonical scientific source into the authoring workspace (refuses to drop edits)
	$(PY) scripts/sync_scientific_source.py --apply
