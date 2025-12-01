.PHONY: test test-cov test-unit test-verbose install-test clean coverage

# Install test dependencies
install-test:
	pip install -e ".[test]"

# Run all tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=app --cov-report=html --cov-report=term-missing

# Run only unit tests
test-unit:
	pytest -m unit

# Run tests with verbose output
test-verbose:
	pytest -v -s

# Run tests and generate coverage report
coverage:
	pytest --cov=app --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Run tests on file change (requires pytest-watch)
watch:
	ptw -- --testmon

# Run all checks
check: test-cov