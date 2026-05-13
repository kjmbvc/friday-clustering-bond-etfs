# Makefile for FRL paper replication
PY    := python
PYT   := pytest -q
SCRIPTS := $(wildcard code/0*.py)

.PHONY: all verify test lint clean distclean help

help:
	@echo "Targets:"
	@echo "  all          run the full pipeline (~45 min)"
	@echo "  verify       run numpy-only closed-form verification (<5 sec)"
	@echo "  test         run pytest unit tests for every math construct"
	@echo "  lint         run ruff on utils/ code/ verification/ tests/"
	@echo "  clean        remove __pycache__ and .pytest_cache"
	@echo "  distclean    also remove output/ and data/raw/"

all: $(SCRIPTS:.py=.done)
	@echo "Pipeline complete."

code/%.done: code/%.py
	$(PY) $<
	@touch $@

verify:
	$(PY) verification/appendix_F_verification.py

test:
	$(PYT) tests/

lint:
	ruff check utils/ code/ verification/ tests/

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache .ruff_cache code/*.done

distclean: clean
	rm -rf output/* data/raw/* data/processed/*
