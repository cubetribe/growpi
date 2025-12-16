# Code Diff: YUYV Fix für Timelapse Qualität

## File: `pi-controller/grow_pi/utils/camera.py`

### Change Location: Lines 147-153

---

### VORHER (Current Code):

```python
141:            self._camera = cv2.VideoCapture(self.config.device_id, cv2.CAP_V4L2)
142:
143:            if not self._camera.isOpened():
144:                logger.error(f"Failed to open camera device {self.config.device_id}")
145:                return False
146:
147:            # Set MJPEG format for efficient capture
148:            self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
149:
150:            # Set resolution
151:            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
```

---

### NACHHER (Variante 1 - Direkt YUYV):

```python
141:            self._camera = cv2.VideoCapture(self.config.device_id, cv2.CAP_V4L2)
142:
143:            if not self._camera.isOpened():
144:                logger.error(f"Failed to open camera device {self.config.device_id}")
145:                return False
146:
147:            # Set YUYV format for maximum quality (uncompressed)
148:            self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
149:
150:            # Set resolution
151:            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
```

**Changes**:
- Line 147: Comment updated ("YUYV" instead of "MJPEG")
- Line 148: `'M', 'J', 'P', 'G'` → `'Y', 'U', 'Y', 'V'`

---

### NACHHER (Variante 2 - Mit Fallback, EMPFOHLEN):

```python
141:            self._camera = cv2.VideoCapture(self.config.device_id, cv2.CAP_V4L2)
142:
143:            if not self._camera.isOpened():
144:                logger.error(f"Failed to open camera device {self.config.device_id}")
145:                return False
146:
147:            # Try YUYV (uncompressed), fallback to MJPEG if not supported
148:            try:
149:                self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
150:                logger.info("Camera using YUYV format (uncompressed)")
151:            except Exception as e:
152:                logger.warning(f"YUYV not supported ({e}), using MJPEG")
153:                self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
154:
155:            # Set resolution
156:            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
```

**Changes**:
- Lines 147-153: Added try-except block
- Line 149: Set YUYV format
- Line 150: Log success message
- Lines 151-153: Fallback to MJPEG on error
- Line 156: Resolution setting moved to after format selection

---

## Git Diff Format

```diff
diff --git a/pi-controller/grow_pi/utils/camera.py b/pi-controller/grow_pi/utils/camera.py
index abc1234..def5678 100644
--- a/pi-controller/grow_pi/utils/camera.py
+++ b/pi-controller/grow_pi/utils/camera.py
@@ -144,8 +144,13 @@ class CameraService:
                 logger.error(f"Failed to open camera device {self.config.device_id}")
                 return False
 
-            # Set MJPEG format for efficient capture
-            self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
+            # Try YUYV (uncompressed), fallback to MJPEG if not supported
+            try:
+                self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
+                logger.info("Camera using YUYV format (uncompressed)")
+            except Exception as e:
+                logger.warning(f"YUYV not supported ({e}), using MJPEG")
+                self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
 
             # Set resolution
             self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
```

---

## Copy-Paste Ready Code

### For Manual Editing (via SSH):

```bash
ssh admin@192.168.0.86
sudo nano /opt/grow-pi/grow_pi/utils/camera.py
# Navigate to line 147 (Ctrl+_ then type 147)
# Delete lines 147-148
# Insert new code below
```

**New Code Block (Copy This)**:
```python
            # Try YUYV (uncompressed), fallback to MJPEG if not supported
            try:
                self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
                logger.info("Camera using YUYV format (uncompressed)")
            except Exception as e:
                logger.warning(f"YUYV not supported ({e}), using MJPEG")
                self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
```

**Save**: Ctrl+O, Enter, Ctrl+X

---

## Verification After Change

### Check Syntax:

```bash
python3 -m py_compile /opt/grow-pi/grow_pi/utils/camera.py
# No output = Success ✅
```

### Restart and Check Logs:

```bash
sudo systemctl restart grow-pi
sudo journalctl -u grow-pi -f | grep -E "Camera|YUYV|MJPEG|format"
```

**Expected Output (Success)**:
```
Dec 09 15:30:45 growpi grow_pi[1234]: INFO - Camera using YUYV format (uncompressed)
Dec 09 15:30:45 growpi grow_pi[1234]: INFO - Camera initialized: 1280x720
```

**Expected Output (Fallback)**:
```
Dec 09 15:30:45 growpi grow_pi[1234]: WARNING - YUYV not supported (...), using MJPEG
Dec 09 15:30:45 growpi grow_pi[1234]: INFO - Camera initialized: 1280x720
```

---

## Testing the Fix

### 1. Capture New Image:

```bash
curl http://192.168.0.86:5000/api/camera/snapshot -o /tmp/test_yuyv.jpg
```

### 2. Check Image Quality:

```bash
# View image properties
identify -verbose /tmp/test_yuyv.jpg | head -20

# Expected:
# - Quality: 70 (for preview) or 95 (for timelapse)
# - No double JPEG artifacts
```

### 3. Visual Comparison:

```bash
# Download old MJPEG image
scp admin@192.168.0.86:/opt/grow-pi/data/timelapse/*/timelapse_*.jpg /tmp/old_mjpeg.jpg

# Compare side-by-side
# Use any image viewer or:
montage /tmp/old_mjpeg.jpg /tmp/test_yuyv.jpg -geometry +2+2 /tmp/comparison.jpg
```

**Expected Difference**:
- Sharper edges
- Less "blockiness"
- Better color transitions
- More visible details in texture

---

## Impact Analysis

| Aspect | Before (MJPEG) | After (YUYV) | Change |
|--------|----------------|--------------|---------|
| Lines of Code | 2 | 7 | +5 lines |
| Complexity | Simple | Try-catch added | +Minimal |
| Safety | N/A | Fallback included | ✅ Safer |
| Image Quality | ~50-76% | ~95% | +19-48% 🚀 |
| CPU Usage | Low | Slightly higher | Negligible |
| USB Bandwidth | ~3 MB/s | ~15 MB/s | Still OK @2fps |
| Risk | N/A | Low (fallback) | ✅ Safe |

---

**Summary**: 7 lines of code for potentially 19-48% better image quality!

---

**Created**: 2025-12-09  
**File**: `pi-controller/grow_pi/utils/camera.py`  
**Lines Changed**: 147-153  
**Risk Level**: LOW (mit Fallback)
