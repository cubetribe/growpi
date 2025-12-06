# GrowPi Test Suite

## Running Tests

### Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=grow_pi --cov-report=term-missing
```

### Run Specific Test Files

```bash
# Run only curve interpolation tests
pytest tests/unit/test_curve_interpolation.py

# Run specific test class
pytest tests/unit/test_curve_interpolation.py::TestMidnightWraparound

# Run specific test function
pytest tests/unit/test_curve_interpolation.py::TestMidnightWraparound::test_midnight_exact
```

### Test Options

```bash
# Show local variables on failures
pytest -l

# Stop on first failure
pytest -x

# Run last failed tests only
pytest --lf

# Show test durations
pytest --durations=10
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── README.md                      # This file
└── unit/
    ├── __init__.py
    └── test_curve_interpolation.py  # Curve interpolation tests
```

## Test Coverage

The test suite includes:

- **62 unit tests** for curve interpolation
- **100% coverage** of `interpolate_curve()` function
- Edge cases: empty curves, single points, midnight wraparound
- Real-world scenarios: sunrise/sunset, 18/6 schedules, EOD treatments

## Critical Safety Tests

These tests ensure plant safety by validating:

1. **Midnight Wraparound** - Correct interpolation across 23:59 → 00:00
2. **Intensity Bounds** - All values stay within 0-100%
3. **Time Precision** - Minute-level accuracy (seconds ignored)
4. **Edge Cases** - Empty curves, single points, invalid data

## Fixtures

Available test fixtures (see `conftest.py`):

- `simple_curve` - Basic 2-point curve
- `full_day_curve` - Realistic daily light cycle
- `midnight_wraparound_curve` - Tests midnight transitions
- `single_point_curve` - Edge case testing
- `empty_curve` - Edge case testing
- `dawn_curve` - Sunrise simulation
- `dusk_curve` - Sunset simulation

## Adding New Tests

1. Create test file in `tests/unit/`
2. Import fixtures from `conftest.py`
3. Use descriptive test names with `test_` prefix
4. Group related tests in classes
5. Add docstrings explaining what's tested

Example:

```python
class TestNewFeature:
    def test_basic_functionality(self, simple_curve):
        """Test basic feature behavior."""
        result = my_function(simple_curve)
        assert result == expected_value
```

## Continuous Integration

TODO: Add CI/CD pipeline to run tests on:
- Every commit
- Pull requests
- Before deployment to Raspberry Pi

## Known Limitations

- Tests run on development machine, not actual Raspberry Pi hardware
- GPIO/pigpio functions require mocking for unit tests
- Real sensor data not tested (only mock data)
