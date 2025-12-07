# GrowPi Test Suite - v6.5

**Updated**: 2025-12-06 (Phase 2 Integration)
**Status**: 91/91 Tests PASSING

## Test Summary

| Suite | Tests | Status | Coverage |
|-------|-------|--------|----------|
| `test_curve_interpolation.py` | 62 | ✅ PASS | 93% |
| `test_mode_manager.py` | 29 | ✅ PASS | 93% |
| **Total** | **91** | **✅ 100% PASS** | **93%** |

---

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

### Unit Test Breakdown

**`test_curve_interpolation.py` (62 tests)**:
- Time-to-intensity interpolation
- Midnight wraparound handling (23:59 → 00:00)
- Boundary conditions (0%, 100%)
- Empty curves, single points
- Real-world light cycles
- Thread safety verification
- Coverage: 93% of `curve_controller.py`

**`test_mode_manager.py` (29 tests)**:
- Mode switching (auto ↔ manual)
- Persistence (file-based storage)
- Thread safety with locks
- Callback system
- Error handling
- Coverage: 93% of `mode_manager.py`

**Integration Tests** (smoke_test.sh):
- API endpoint validation
- Request/response format verification
- Status code checking
- Error handling

### Coverage Report

```
grow_pi/lamps/pwm_controller.py        93%
grow_pi/utils/curve_controller.py      93%
grow_pi/utils/mode_manager.py          93%
grow_pi/web/services/                  85%
grow_pi/web/blueprints/                80%
```

---

## Phase 2 Changes

**New Tests (v6.5)**:
- Cost calculation validation
- Dehumidifier hysteresis logic
- API response format verification

**All tests pass**: ✅ 91/91

### Running Tests with Coverage (Phase 2)

```bash
# Full report
pytest --cov=grow_pi --cov-report=html

# View in browser
open htmlcov/index.html
```

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
