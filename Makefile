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
 tests/test_transitions.py tests/test_transition_cli.py \
 src/nfl_value/admission.py src/nfl_value/admission_cli.py tests/test_admission.py \
 src/nfl_value/review_bundle.py src/nfl_value/review_cli.py tests/test_review_bundle.py \
 src/nfl_value/recovery_io.py src/nfl_value/recovery.py src/nfl_value/recovery_cli.py tests/test_recovery.py \
 src/nfl_value/readiness.py src/nfl_value/refresh_candidate.py src/nfl_value/readiness_cli.py tests/test_readiness.py \
 src/nfl_value/launch_bundle.py src/nfl_value/launch_cli.py tests/test_launch_bundle.py \
 src/nfl_value/production.py src/nfl_value/production_cli.py tests/test_production.py \
 src/nfl_value/qb_math.py src/nfl_value/qb_recovery.py src/nfl_value/qb_simulation.py \
 src/nfl_value/qb_recovery_cli.py src/nfl_value/qb_variance_control.py src/nfl_value/research_roster.py \
 tests/test_qb_math.py tests/test_qb_recovery.py tests/test_research_roster.py \
 src/nfl_value/variance_mixture.py src/nfl_value/multiseason_math.py src/nfl_value/multiseason.py \
 src/nfl_value/multiseason_simulation.py src/nfl_value/multiseason_cli.py src/nfl_value/multiseason_control.py src/nfl_value/defense_variance.py \
 tests/test_variance_mixture.py tests/test_multiseason.py

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
