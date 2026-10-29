.PHONY: test check web-check python-quality coverage coverage-report

PYTHON ?= python3
# Incremental format adoption; expand this list when substantially editing modules.
PYTHON_FORMAT_FILES = src/nfl_value/baseline_cli.py tests/test_release_reliability.py \
 src/nfl_value/weekly_rosters.py src/nfl_value/roster_inputs.py src/nfl_value/roster_cli.py \
 tests/test_roster_inputs.py src/nfl_value/contrast_math.py src/nfl_value/contrast_cohorts.py \
 src/nfl_value/contrasts.py src/nfl_value/contrast_cli.py tests/test_contrasts.py tests/test_contrast_cli.py \
 src/nfl_value/calibration.py src/nfl_value/calibration_math.py src/nfl_value/calibration_cli.py \
 tests/test_calibration.py tests/test_calibration_cli.py \
 src/nfl_value/transitions.py src/nfl_value/transition_cli.py \
 tests/test_transitions.py tests/test_transition_cli.py

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
