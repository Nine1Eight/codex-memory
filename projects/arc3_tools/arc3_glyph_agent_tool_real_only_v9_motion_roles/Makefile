SHELL := /bin/bash
PYTHON ?= python3
STARTER ?= $(HOME)/arc3_api_run/ARC-AGI-3-Agents

.PHONY: audit verify-real install-into-starter patch-loader hotfix probe summarize-probe analyze-reflection play-real analyze clean

audit:
	$(PYTHON) scripts/no_mock_audit.py

verify-real:
	$(PYTHON) scripts/verify_real_starter.py "$(STARTER)" agent/my_agent.py

install-into-starter:
	bash scripts/install_into_starter.sh "$(STARTER)"

patch-loader:
	bash scripts/patch_real_loader.sh "$(STARTER)"

hotfix:
	bash scripts/hotfix_preview_syntax.sh "$(STARTER)"

probe:
	bash scripts/run_real_probe.sh "$(STARTER)" "$${GAME:-tr87}" "$${STEPS:-40}"

summarize-probe:
	$(PYTHON) scripts/summarize_probe.py "$(STARTER)/logs"

analyze-reflection:
	$(PYTHON) scripts/analyze_reflection.py "$(STARTER)/logs"

play-real:
	bash scripts/run_real_local.sh "$(STARTER)"

analyze:
	$(PYTHON) scripts/analyze_logs.py "$(STARTER)/logs"

clean:
	rm -rf __pycache__ agent/__pycache__ scripts/__pycache__
	find . -name "*.pyc" -delete
