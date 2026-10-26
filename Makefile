.PHONY: test check web-check python-quality coverage coverage-report

PYTHON ?= python3
# Incremental format adoption; expand this list when substantially editing modules.
PYTHON_FORMAT_FILES = src/nfl_value/baseline_cli.py tests/test_release_reliability.py

python-quality:
	$(PYTHON) -m ruff check src scripts tests
	$(PYTHON) -m ruff format --check $(PYTHON_FORMAT_FILES)

coverage:
	PYTHONPATH=src $(PYTHON) -m coverage run -m unittest discover -s tests -v
	$(MAKE) coverage-report

coverage-report:
	$(PYTHON) -m coverage report
	$(PYTHON) -m coverage html
	$(PYTHON) -m coverage xml
	$(PYTHON) -m coverage json

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

web-check:
	npm --prefix web run check

check: python-quality test web-check
	$(PYTHON) -m compileall -q src scripts tests
	git diff --check
	git diff --cached --check
