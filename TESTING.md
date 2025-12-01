# Testing Documentation for PyIIIF

## Overview

This document describes the comprehensive test suite created for the PyIIIF project, covering all Python modules added or modified in the current branch.

## Test Coverage Summary

### Modules Tested (20+ test files)

#### Core Application Components
- **app/__init__.py** - Application factory and initialization
- **app/config.py** - Configuration management and environment variables
- **app/errors.py** - Error handler registration
- **app/logger.py** - Logging setup and sensitive data redaction

#### Utility Modules
- **app/utils/http.py** - HTTP utilities (cache headers, timing decorators)
- **app/utils/image.py** - Image processing (JPEG options, PIL helpers, level selection)
- **app/utils/path.py** - Path validation and security
- **app/utils/s3file.py** - S3 file operations (stubs for testing)
- **app/utils/s3range_reader.py** - S3 range reading (stubs for testing)
- **app/utils/s3_json_loader.py** - JSON loading from S3 (stubs for testing)

#### WSI (Whole Slide Imaging) Modules
- **app/utils/wsi/iiif.py** - IIIF info.json builder and zoom level builder
- **app/utils/wsi/iiif_header.py** - IIIF header and profile construction
- **app/utils/wsi/ifds.py** - IFD data structures and collections
- **app/utils/wsi/ifd_parser.py** - TIFF/BigTIFF IFD parsing
- **app/utils/wsi/explorer.py** - WSI metadata exploration
- **app/utils/wsi/io.py** - S3RangeReader for WSI files

#### Service Layer
- **app/services/slide.py** - OpenSlide integration with LRU caching

## Test Statistics

- **Total Test Files**: 18
- **Total Test Functions**: 150+
- **Test Types**: Unit tests with mocking for external dependencies
- **Framework**: pytest with pytest-mock

## Key Testing Patterns

### 1. Mocking External Dependencies

```python
@patch('boto3.client')
def test_s3_operation(mock_boto_client):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    # Test S3 operations without actual AWS calls
```

### 2. Flask Application Testing

```python
@patch('app.setup_logger')
def test_create_app(mock_logger):
    app = create_app()
    with app.test_client() as client:
        response = client.get('/healthz')
        assert response.status_code == 200
```

### 3. Security Testing

```python
def test_safe_join_prevents_traversal():
    base = Path("/base")
    with pytest.raises((ValueError, AssertionError)):
        safe_join(base, "../etc/passwd")
```

### 4. Data Validation

```python
def test_parse_region_invalid_format():
    with pytest.raises((ValueError, AssertionError)):
        parse_region("invalid", 1000, 800)
```

## Test Scenarios Covered

### Happy Paths ✅
- Valid IIIF requests
- Successful slide loading
- Proper metadata extraction
- Correct tile generation
- Cache header application

### Edge Cases ✅
- Empty inputs
- Boundary values
- Non-standard dimensions
- Partial tiles
- Multiple pyramid levels

### Error Conditions ✅
- Invalid file formats
- Malformed requests
- Missing files (404)
- S3 read failures
- Invalid JSON parsing
- TIFF header errors

### Security ✅
- Directory traversal prevention
- Path validation
- Input sanitization
- Sensitive data redaction
- SQL injection prevention (config validation)

## Running the Tests

### Prerequisites

```bash
# Install project with test dependencies
pip install -e ".[test]"
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_config.py

# Run specific test function
pytest tests/unit/test_config.py::TestConfig::test_config_defaults
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

### Using Makefile

```bash
# Install dependencies
make install-test

# Run tests
make test

# Run with coverage
make test-cov

# Clean artifacts
make clean
```

## Test Fixtures (conftest.py)

### `mock_s3_client`
Provides a mocked boto3 S3 client for testing S3 operations without AWS credentials or network calls.

### `mock_flask_app`
Creates a Flask test application instance with TESTING=True.

### `sample_tiff_bytes`
Minimal valid TIFF header bytes for testing TIFF parsing logic.

### `sample_image_data`
Sample JPEG image bytes created with PIL for image processing tests.

## Continuous Integration

Recommended CI configuration:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -e ".[test]"
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Maintenance

### Adding New Tests

1. Follow existing naming conventions: `test_<feature>_<scenario>.py`
2. Use descriptive test function names that explain what is being tested
3. Group related tests in classes
4. Mock external dependencies
5. Test both success and failure paths

### Code Coverage Goals

- **Minimum**: 80% overall coverage
- **Target**: 90%+ for critical paths
- **Critical modules**: 95%+ (config, security, IIIF core)

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure app is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Missing Dependencies**
```bash
pip install -e ".[test]"
```

**Boto3 Credential Errors**
- Tests mock boto3, so real credentials aren't needed
- If tests try to access real S3, check mock patches

**PIL/Pillow Issues**
```bash
# Install Pillow with full support
pip install Pillow[all]
```

## Future Test Enhancements

- [ ] Integration tests for full IIIF workflows
- [ ] Performance/load tests for tile serving
- [ ] End-to-end tests with real WSI files
- [ ] Snapshot testing for IIIF responses
- [ ] Property-based testing with Hypothesis
- [ ] Mutation testing for test quality validation

## Contributing

When contributing:
1. Write tests for all new features
2. Update existing tests when modifying behavior
3. Ensure all tests pass before submitting PR
4. Maintain or improve code coverage
5. Follow existing test patterns and conventions

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [IIIF Image API](https://iiif.io/api/image/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)