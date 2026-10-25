.PHONY: test check web-check

PYTHON ?= python3

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

web-check:
	npm --prefix web run check

check: test web-check
	$(PYTHON) -m compileall -q src scripts tests
	git diff --check
	git diff --cached --check
