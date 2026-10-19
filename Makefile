.PHONY: test check

PYTHON ?= python3

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

check: test
	$(PYTHON) -m compileall -q src scripts tests
	git diff --check
	git diff --cached --check
