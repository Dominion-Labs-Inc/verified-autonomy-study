PYTHON ?= python3

.PHONY: tasks split inventory sample-sizes prereg

tasks:
	$(PYTHON) scripts/fetch_tasks.py

split:
	$(PYTHON) scripts/split_tasks.py

inventory:
	$(PYTHON) scripts/inventory_submissions.py

sample-sizes:
	$(PYTHON) scripts/sample_sizes.py

prereg: tasks split inventory sample-sizes
