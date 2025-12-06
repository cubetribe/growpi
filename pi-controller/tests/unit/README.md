# Unit Tests - ModeManager

## Overview

Comprehensive unit tests for the `ModeManager` class, which provides centralized mode management for the GrowPi system to prevent race conditions during lamp control operations.

## Test Coverage: 93%

**Total:** 29 tests across 6 test classes

### Test Classes

#### 1. TestModeManagerDefaults (3 tests)
- `test_default_mode_is_auto` - Verifies default mode is 'auto'
- `test_is_auto_returns_true_by_default` - Checks is_auto() helper
- `test_is_manual_returns_false_by_default` - Checks is_manual() helper

#### 2. TestModeManagerSetMode (6 tests)
- `test_set_mode_auto` - Tests setting to auto mode
- `test_set_mode_manual` - Tests setting to manual mode
- `test_invalid_mode_rejected` - Rejects invalid mode strings
- `test_set_same_mode_returns_false` - No-op when mode unchanged
- `test_empty_string_mode_rejected` - Rejects empty string
- `test_none_mode_rejected` - Rejects None value

#### 3. TestModeManagerPersistence (5 tests)
- `test_mode_persistence_to_file` - Verifies file write on mode change
- `test_mode_loaded_from_file` - Loads mode from existing file
- `test_invalid_mode_in_file_defaults_to_auto` - Handles corrupted data
- `test_missing_mode_file_defaults_to_auto` - Handles missing file
- `test_corrupted_mode_file_defaults_to_auto` - Handles read errors

#### 4. TestModeManagerBooleanHelpers (2 tests)
- `test_is_auto_returns_correct_bool` - Validates is_auto() accuracy
- `test_is_manual_returns_correct_bool` - Validates is_manual() accuracy

#### 5. TestModeManagerCallbacks (5 tests)
- `test_callback_registered` - Callback registration
- `test_callback_called_on_mode_change` - Callback invocation
- `test_callback_not_called_on_same_mode` - No callback on no-op
- `test_multiple_callbacks_registered` - Multiple callback support
- `test_callback_exception_does_not_crash` - Error isolation

#### 6. TestModeManagerThreadSafety (4 tests)
- `test_thread_safety_concurrent_reads` - 10 threads, 100 reads each
- `test_thread_safety_concurrent_writes` - 5 threads, 50 writes each
- `test_thread_safety_concurrent_read_write` - Mixed read/write operations
- `test_thread_safety_callback_registration` - Callbacks during mode changes

#### 7. TestModeManagerEdgeCases (4 tests)
- `test_get_mode_returns_string` - Type validation
- `test_mode_case_sensitivity` - Rejects uppercase modes
- `test_mode_with_whitespace_rejected` - Rejects whitespace-padded input
- `test_rapid_mode_changes` - 100 rapid mode toggles

## Running Tests

### Full Test Suite
```bash
cd pi-controller
source venv/bin/activate
python -m pytest tests/unit/test_mode_manager.py -v
```

### With Coverage Report
```bash
python -m pytest tests/unit/test_mode_manager.py \
  --cov=grow_pi.utils.mode_manager \
  --cov-report=term-missing
```

### Single Test Class
```bash
python -m pytest tests/unit/test_mode_manager.py::TestModeManagerThreadSafety -v
```

### Single Test
```bash
python -m pytest tests/unit/test_mode_manager.py::TestModeManagerThreadSafety::test_thread_safety_concurrent_reads -v
```

## Test Fixtures

### `temp_mode_file(tmp_path)`
Creates a temporary mode file in pytest's tmp_path directory. Automatically cleaned up after test completion.

**Usage:**
```python
def test_example(temp_mode_file):
    # temp_mode_file is a string path to temporary file
    with open(temp_mode_file, 'w') as f:
        f.write("manual")
```

### `mode_manager_instance(temp_mode_file)`
Provides a fresh ModeManager instance with isolated mode file for each test. Prevents test pollution.

**Usage:**
```python
def test_example(mode_manager_instance):
    # Each test gets clean ModeManager
    mode_manager_instance.set_mode("manual")
    assert mode_manager_instance.get_mode() == "manual"
```

## Critical Test Scenarios

### Thread Safety (Most Important)
These tests validate that ModeManager is safe for concurrent access from multiple threads:

1. **Concurrent Reads**: 1000 total reads (10 threads × 100 each)
2. **Concurrent Writes**: 250 total writes (5 threads × 50 each)
3. **Mixed Operations**: 3 reader threads + 2 writer threads
4. **Callback Registration**: Callbacks added during active mode changes

**Why Critical?**
- Flask API runs in threaded mode
- Multiple endpoints may access mode simultaneously
- Lamp controller and data logger run concurrently
- Race conditions could cause:
  - Invalid mode states
  - Lamp control conflicts
  - Callback corruption

### Persistence Tests
Validate crash recovery and mode retention:

1. **File Write**: Mode changes persisted to `/tmp/growpi_mode.txt`
2. **File Read**: Mode restored on ModeManager initialization
3. **Error Handling**: Corrupted/missing files default to 'auto' (safe mode)

**Why Critical?**
- System crash → mode must default to 'auto' for plant safety
- `/tmp` cleared on reboot → ensures safe startup
- Invalid file data must not crash system

### Callback Tests
Ensure mode change notifications work correctly:

1. **Callback Invocation**: Called with (old_mode, new_mode)
2. **Multiple Callbacks**: All callbacks notified
3. **Exception Isolation**: One failing callback doesn't break others

**Why Critical?**
- Lamp controller registers callback to respond to mode changes
- Data logger may register callback for event logging
- Callback exceptions must not prevent mode change

## Coverage Analysis

**93% Coverage** - Missing Lines:
- Lines 38-40: Singleton `get_mode_manager()` function (tested implicitly)
- Lines 81-82: File write error logging (would require mocking filesystem)

**Why 93% is Acceptable:**
- All critical code paths tested
- Missing lines are error logging (defensive code)
- Testing file I/O errors requires complex mocking
- Real-world file write failures extremely rare

## Known Test Patterns

### Using Mocks for Callbacks
```python
from unittest.mock import Mock

callback = Mock()
mode_manager.register_callback(callback)
mode_manager.set_mode("manual")

# Verify callback was called
callback.assert_called_once_with("auto", "manual")
```

### Testing Thread Safety
```python
import threading

def worker():
    for _ in range(100):
        mode_manager.set_mode("manual")

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# Validate final state
assert mode_manager.get_mode() in MODES
```

### Testing File Persistence
```python
# Write mode
manager1 = ModeManager()
manager1.set_mode("manual")

# Read mode (new instance)
manager2 = ModeManager()
assert manager2.get_mode() == "manual"
```

## Future Test Additions

Potential tests to add if requirements change:

1. **Performance Tests**: Measure mode switch latency
2. **Load Tests**: Stress test with 1000+ threads
3. **Integration Tests**: Test with real Flask endpoints
4. **Memory Leak Tests**: Long-running mode changes
5. **File Permissions Tests**: Restricted filesystem access

## Debugging Failed Tests

### Import Errors
```bash
# Ensure grow_pi package is in PYTHONPATH
export PYTHONPATH="/path/to/pi-controller:$PYTHONPATH"
```

### File Permission Errors
```bash
# Tests create files in /tmp - ensure write permissions
ls -la /tmp/growpi_mode.txt
```

### Thread Timeout Issues
```bash
# Increase test timeout if hardware is slow
python -m pytest tests/unit/test_mode_manager.py --timeout=60
```

## Maintenance Notes

**When to Update Tests:**
1. Adding new modes beyond 'auto'/'manual'
2. Changing mode file location
3. Adding new callback signature parameters
4. Modifying thread-safety mechanisms
5. Adding new ModeManager methods

**Test Philosophy:**
- **Unit tests** test ModeManager in isolation
- Use **mocks** for external dependencies
- Use **tmp_path** for file operations
- **No network calls** in unit tests
- Each test is **independent** and **idempotent**

## Related Documentation

- `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/utils/mode_manager.py` - Source code
- `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/docs/ARCHITECTURE.md` - System design
- `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/docs/SPEC_RASPBERRY_PI.md` - Hardware spec

---

**Last Updated:** 2025-12-06
**Test Framework:** pytest 9.0.1
**Python Version:** 3.13
**Coverage:** 93%
