# Timelapse Qualität - Quick Fix Guide

**Problem**: Bilder sehen schlecht aus trotz JPEG Quality 95  
**Root Cause**: MJPEG Doppel-Kompression (Kamera → OpenCV → JPEG)  
**Fix**: Unkomprimiertes YUYV Format verwenden  

---

## Option A: Schneller Test (SSH)

```bash
# 1. SSH zum Pi
ssh admin@192.168.0.86

# 2. Check welche Formate die Kamera unterstützt
v4l2-ctl --list-formats-ext -d /dev/video0

# 3. Suche nach YUYV in der Ausgabe
# Wenn vorhanden: YUYV wird unterstützt ✅
# Wenn nicht: Nur MJPEG verfügbar ❌
```

---

## Option B: Code Fix (1 Zeile ändern)

**File**: `pi-controller/grow_pi/utils/camera.py`  
**Line**: 148  

### Variante 1: Direkt YUYV (risikoreicher)

```python
# VORHER:
self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

# NACHHER:
self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
```

### Variante 2: Mit Fallback (sicherer, empfohlen)

```python
# VORHER (Zeile 148):
self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

# NACHHER (Zeile 148-153):
try:
    self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
    logger.info("Camera using YUYV format (uncompressed)")
except Exception as e:
    logger.warning(f"YUYV not supported ({e}), using MJPEG")
    self._camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
```

---

## Deployment

```bash
# 1. Code ändern (lokal)
# 2. Test lokal (optional)
# 3. Deploy zum Pi
scp pi-controller/grow_pi/utils/camera.py admin@192.168.0.86:/opt/grow-pi/grow_pi/utils/

# 4. Restart Service
ssh admin@192.168.0.86 "sudo systemctl restart grow-pi"

# 5. Check Logs
ssh admin@192.168.0.86 "sudo journalctl -u grow-pi -f"

# Erwartete Log-Zeile:
# "Camera using YUYV format (uncompressed)"
# ODER
# "YUYV not supported (...), using MJPEG"
```

---

## Testing

```bash
# 1. Capture Testbild
curl http://192.168.0.86:5000/api/camera/snapshot -o test_after_fix.jpg

# 2. Vergleiche mit vorherigem Bild
# - Schärfere Details?
# - Weniger JPEG-Artefakte?
# - Weniger "Blockiness"?

# 3. Check Filesize
ls -lh test_after_fix.jpg

# Erwartung: Filesize ähnlich oder größer (wegen besserer Qualität)
```

---

## Rollback (falls Probleme)

```bash
# 1. SSH zum Pi
ssh admin@192.168.0.86

# 2. Edit Datei direkt
sudo nano /opt/grow-pi/grow_pi/utils/camera.py

# 3. Suche Zeile 148 (Ctrl+W für Search)
# 4. Ändere YUYV zurück zu MJPEG
# 5. Save (Ctrl+O) und Exit (Ctrl+X)

# 6. Restart
sudo systemctl restart grow-pi
```

---

## Erwartete Verbesserung

| Metrik | Vorher (MJPEG) | Nachher (YUYV) | Verbesserung |
|--------|----------------|----------------|--------------|
| Effektive Qualität | ~50-76% | ~95% | +19-48% |
| JPEG Artefakte | Stark | Minimal | ✅ |
| Schärfe | Reduziert | Maximal | ✅ |
| CPU-Last | Niedrig | Etwas höher | ⚠️ (vernachlässigbar) |
| USB-Bandbreite | Niedrig | Höher | ⚠️ (bei 2 FPS OK) |

---

## Troubleshooting

### Problem: "YUYV not supported"
**Lösung**: Kamera unterstützt nur MJPEG → Alternative Kamera erwägen

### Problem: Service startet nicht nach Änderung
**Check**: `sudo journalctl -u grow-pi -n 50`  
**Lösung**: Syntax-Fehler im Code → Rollback

### Problem: Bilder werden nicht besser
**Mögliche Ursachen**:
1. Kamera-Hardware ist Bottleneck
2. Belichtung suboptimal → Versuche manuelle Exposure (siehe Haupt-Report)
3. Autofokus unscharf → Ggf. manuell fokussieren

---

## Alternative: Bessere Kamera

Falls YUYV keine Verbesserung bringt, könnte Hardware-Upgrade helfen:

**Empfehlung**: Raspberry Pi Camera Module v2
- Preis: ~25€
- Auflösung: 8MP (3280x2464)
- Direkter CSI-Anschluss (keine USB-Kompression)
- Besserer Sensor als Budget-Webcam
- Manuelle Steuerung via `picamera2` Library

**Nachteil**: Erfordert Code-Anpassung (OpenCV → picamera2)

---

**Erstellt**: 2025-12-09  
**Version**: v6.18.0
