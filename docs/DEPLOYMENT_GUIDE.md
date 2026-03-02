# GrowPi Deployment Guide - v6.5 Refactoring

**Status**: 🚧 READY FOR TESTING
**Branch**: `refactoring/phase-1-modularization`
**Last Updated**: 2025-12-06

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Local Testing](#local-testing)
3. [Test Pi Deployment](#test-pi-deployment)
4. [Production Deployment](#production-deployment)
5. [Rollback Plan](#rollback-plan)
6. [Monitoring](#monitoring)

---

## Pre-Deployment Checklist

Before deploying to any environment, verify the following:

### Code Quality Gates

```bash
# 1. Verify branch is correct
git branch --show-current
# Expected output: refactoring/phase-1-modularization

# 2. Run unit tests
cd pi-controller
source venv/bin/activate
pytest tests/ -v --cov=grow_pi
# Expected: 91/91 tests PASSED

# 3. Run smoke tests
./smoke_test.sh
# Expected: All endpoint tests PASSED

# 4. Python syntax check
python -m py_compile grow_pi/**/*.py

# 5. JavaScript syntax check
cd grow_pi/web/static
for file in js/**/*.js; do node -c "$file"; done
```

### Required Files

Verify these files exist and are updated:

- [ ] `pi-controller/grow_pi/web/api.py` - Updated with costs + dehumidifier endpoints
- [ ] `pi-controller/grow_pi/web/app.py` - Flask App Factory
- [ ] `pi-controller/grow_pi/web/blueprints/*.py` - 6+ API blueprints
- [ ] `pi-controller/grow_pi/web/static/js/modules/*.js` - JavaScript modules
- [ ] `pi-controller/grow_pi/config/room_config.json` - Extended config
- [ ] `pi-controller/tests/unit/*.py` - Unit tests
- [ ] `CHANGELOG.md` - Updated with v6.5 entry

### Configuration

Update before deployment:

**`room_config.json`:**
```json
{
  "costs": {
    "kwh_price": 0.30,
    "currency": "EUR"
  },
  "dehumidifier": {
    "enabled": true,
    "target_humidity": 60,
    "hysteresis": {"upper": 65, "lower": 55},
    "min_run_time": 60,
    "min_off_time": 60
  },
  "devices": {
    "bf36487f67d7bb8fc18buj": "Main Light",
    ...
  }
}
```

---

## Local Testing

### 1. Run Test Environment

Start the Pi simulation locally:

```bash
cd pi-controller/test_environment
python run_local.py
```

Expected output:
```
* Running on http://127.0.0.1:5000
DHT22 mock initialized (22°C, 60%)
DataLogger mock initialized
```

### 2. Verify Web Interface

Open in browser: `http://localhost:5000`

Check all tabs are functional:
- [ ] **Steuerung** - Lamp sliders work
- [ ] **Kurven** - Curve editor loads
- [ ] **Verlauf** - Charts display
- [ ] **Room** - Dehumidifier status shows
- [ ] **Kosten** - Cost breakdown displays

### 3. Run API Tests

In another terminal:

```bash
cd pi-controller
./smoke_test.sh

# Or manually test new endpoints:
curl http://localhost:5000/api/costs?period=today
curl http://localhost:5000/api/dehumidifier/status
curl http://localhost:5000/api/costs/config
```

### 4. Check Logs

Monitor console output for errors:

```bash
# In run_local.py terminal
tail -f test_environment/app.log
```

---

## Test Pi Deployment

### Prerequisites

- Second Raspberry Pi with identical hardware (or test network VLAN)
- SSH access configured
- Same OS version as production Pi

### Deployment Steps

```bash
# 1. Connect to Test Pi
ssh admin@<PI_HOST>  # Example: different IP

# 2. Create backup
sudo cp -r /opt/grow-pi /opt/grow-pi.backup.v6.4

# 3. Pull latest code from branch
cd /opt/grow-pi
git fetch origin
git checkout refactoring/phase-1-modularization

# 4. Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# 5. Restart service
sudo systemctl restart grow-pi

# 6. Verify service is running
sudo systemctl status grow-pi
sudo journalctl -u grow-pi -f  # Monitor logs
```

### Test Scenarios (24h minimum)

**Scenario 1: Basic Functionality**
```bash
# Check all tabs load
curl http://<PI_HOST>:5000/api/status
curl http://<PI_HOST>:5000/api/costs?period=today
curl http://<PI_HOST>:5000/api/dehumidifier/status

# Verify response format matches v6.4
```

**Scenario 2: Curve Updates**
```bash
# Edit a curve and save
curl -X PUT http://<PI_HOST>:5000/api/curves/1 \
  -H "Content-Type: application/json" \
  -d '{"curve": [{"time": "06:00", "intensity": 50}]}'

# Verify lights update accordingly
```

**Scenario 3: Dehumidifier Control**
```bash
# Test manual override
curl -X POST http://<PI_HOST>:5000/api/dehumidifier/control \
  -H "Content-Type: application/json" \
  -d '{"action": "on"}'

# Verify Tuya device responds
```

**Scenario 4: Cost Calculation**
```bash
# Check cost breakdown for different periods
curl http://<PI_HOST>:5000/api/costs?period=week
curl http://<PI_HOST>:5000/api/costs?period=month

# Verify calculations are correct
```

**Scenario 5: Stability Test (run continuously)**
```bash
# Monitor for 24 hours
watch -n 60 'curl -s http://<PI_HOST>:5000/api/health | jq'

# Expected: No "500" errors, all services "running"
# Expected CPU usage: < 10%
# Expected Memory: < 150MB
```

### Acceptance Criteria

Before moving to production:

- [ ] All HTTP endpoints respond with 200 OK
- [ ] No 500 Server Errors in logs
- [ ] Lamp intensity updates work
- [ ] Dehumidifier toggles correctly
- [ ] Cost calculations accurate
- [ ] Database logging working (check .db file size growing)
- [ ] Service survives restart
- [ ] No memory leaks over 24h

---

## Production Deployment

### Blue-Green Deployment

Minimize downtime with blue-green strategy:

**Blue** = Current running system (v6.4)
**Green** = New system (v6.5)

```bash
# 1. Start on Blue (production Pi)
# Leave Blue running

# 2. Create parallel environment for Green
ssh admin@<PI_HOST>
sudo mkdir -p /opt/grow-pi-v6.5
sudo chown admin:admin /opt/grow-pi-v6.5

# 3. Deploy Green in parallel
cd /opt/grow-pi-v6.5
git clone <repo> .
git checkout refactoring/phase-1-modularization
source venv/bin/activate
pip install -r requirements.txt

# 4. Test Green (on different port 5001)
# Start manually:
python -m grow_pi.main --port 5001

# Verify all endpoints work

# 5. Atomic switch
sudo systemctl stop grow-pi            # Stop Blue
sleep 5
sudo systemctl start grow-pi-v6.5      # Start Green

# 6. Verify production
curl http://<PI_HOST>:5000/api/health
```

### Gradual Rollout (Alternative)

If multiple Pis:

```bash
# 1. Deploy to Pi-2 first
# 2. Monitor for 24h
# 3. If stable, deploy to Pi-1 (main greenhouse)
```

### Post-Deployment Verification

```bash
# Check service status
sudo systemctl status grow-pi

# Monitor logs
sudo journalctl -u grow-pi --since "30 min ago" -f

# Verify endpoints
curl http://<PI_HOST>:5000/api/status
curl http://<PI_HOST>:5000/api/costs?period=today

# Check database integrity
sqlite3 /opt/grow-pi/data/growpi.db ".tables"
```

---

## Rollback Plan

If critical issues occur:

### Immediate Rollback (< 30 seconds downtime)

```bash
# 1. Stop v6.5
sudo systemctl stop grow-pi

# 2. Restore from backup
sudo rm -rf /opt/grow-pi
sudo cp -r /opt/grow-pi.backup.v6.4 /opt/grow-pi

# 3. Start v6.4
sudo systemctl start grow-pi

# 4. Verify
curl http://<PI_HOST>:5000/api/status
```

### Graceful Rollback (Git reset)

```bash
cd /opt/grow-pi
git checkout main          # Switch to stable branch
git pull origin main

# Restart service
sudo systemctl restart grow-pi

# Verify
sudo journalctl -u grow-pi --since "5 min ago"
```

### When to Rollback

Rollback immediately if:
- [ ] Service crashes (non-recoverable)
- [ ] Database corruption detected
- [ ] API responses show garbled data
- [ ] Memory usage > 300MB (memory leak)
- [ ] CPU usage constantly > 50% (infinite loop)

### What NOT to Rollback For

Continue troubleshooting if:
- [ ] Single HTTP 404 (endpoint typo)
- [ ] Occasional 500 errors (connection blips)
- [ ] Slow response times (network, not code)

---

## Monitoring

### Key Metrics to Watch

**System Health:**
```bash
# CPU Usage
top -b -n 1 | grep grow-pi

# Memory Usage
ps aux | grep grow-pi | grep -v grep

# Disk Space
df -h /opt/grow-pi

# Database Size
du -sh /opt/grow-pi/data/growpi.db
```

**Application Health:**
```bash
# Service Status
sudo systemctl status grow-pi

# Recent Errors
sudo journalctl -u grow-pi -n 50

# Response Times
curl -w "@curl-format.txt" -o /dev/null http://<PI_HOST>:5000/api/status
```

### Alerting Setup

Monitor these logs for issues:

```bash
# Watch for errors
sudo journalctl -u grow-pi -f | grep -i "error\|exception\|failed"

# Watch for database issues
sqlite3 /opt/grow-pi/data/growpi.db "SELECT COUNT(*) FROM sensor_readings LIMIT 1"

# Watch for API failures
curl -s http://<PI_HOST>:5000/api/health | jq '.status'
```

### Performance Baselines

Expected values (after v6.5):

| Metric | Expected | Alert Threshold |
|--------|----------|-----------------|
| Memory Usage | 80-120 MB | > 200 MB |
| CPU Usage | 2-5% | > 20% |
| API Response Time | < 200 ms | > 500 ms |
| Database Size | +10 MB/day | > 100 MB/week (retention issue) |
| Uptime | > 99% | < 98% |

---

## Troubleshooting

### Service Won't Start

```bash
# Check for port conflict
sudo lsof -i :5000

# Check for Python errors
python -m grow_pi.main

# Check permissions
ls -la /opt/grow-pi
```

### Lamp Control Not Working

```bash
# Check GPIO access
ls -la /dev/gpiomem*

# Test PWM directly
python -c "from grow_pi.lamps import PWMController; PWMController().test()"
```

### Database Errors

```bash
# Check integrity
sqlite3 /opt/grow-pi/data/growpi.db "PRAGMA integrity_check"

# Optimize
sqlite3 /opt/grow-pi/data/growpi.db "VACUUM"
```

### API Returns 500 Error

```bash
# Check logs
sudo journalctl -u grow-pi -n 100 -p err

# Check Flask config
curl -i http://<PI_HOST>:5000/api/health
```

---

## Success Criteria

Deployment is successful when:

- [x] Service starts without errors
- [x] All API endpoints respond (200 OK)
- [x] Web interface loads all tabs
- [x] Lamp control works (brightness changes)
- [x] Dehumidifier toggles ON/OFF
- [x] Cost calculations are correct
- [x] Database logging active (file growing)
- [x] No 500 errors in logs for 24h
- [x] Memory usage stable
- [x] CPU usage < 10%

---

## Rollback Verification

After rollback, confirm:

```bash
# Check version
curl http://<PI_HOST>:5000/api/version

# Verify old endpoints work
curl http://<PI_HOST>:5000/api/status
curl http://<PI_HOST>:5000/api/lamps

# Check no new v6.5 features appear
curl http://<PI_HOST>:5000/api/costs  # Should 404
```

---

## Support

**Deployment Issues?**

Check:
1. `CHANGELOG.md` - v6.5 notes
2. `docs/REFACTORING_SUCCESS.md` - Refactoring details
3. `pi-controller/README.md` - Local testing guide

**Contact**: d.westermann@ol-mg.de

---

**Version**: 2025-12-06 v6.5
**Status**: Ready for Test-Pi Deployment
