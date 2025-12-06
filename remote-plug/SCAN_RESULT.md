# ANTELA Smart Plug BLE Scan Result

**Scan durchgeführt am:** 2025-12-06
**Raspberry Pi:** growpi (192.168.0.86)

---

## RESULT

```
Device found: TY
MAC: 18:DE:50:93:13:6D
Tuya-BLE fingerprint: PARTIAL (Service 0x1910, nicht klassisches FFF0/FFF1)
TinyTuya: Nicht direkt unterstützt (WiFi-only)
tuya-ble: Verfügbar, erfordert Cloud-Credentials
```

---

## Detaillierte Analyse

### 1. Gerät gefunden

| Eigenschaft | Wert |
|-------------|------|
| **Name** | TY |
| **MAC-Adresse** | 18:DE:50:93:13:6D |
| **Typ** | LE Public |
| **RSSI** | -74 dBm (gute Signalstärke) |
| **Verbindung** | Erfolgreich hergestellt |

### 2. GATT Services

Das Gerät bietet folgende BLE-Services:

```
Service: 00001800-0000-1000-8000-00805f9b34fb (Generic Access)
  - 00002a00: Device Name (read)
  - 00002a01: Appearance (read)
  - 00002ac9: Resolvable Private Address (read)

Service: 00001801-0000-1000-8000-00805f9b34fb (Generic Attribute)
  - 00002a05: Service Changed (indicate)
  - 00002b29: Client Supported Features (read, write)
  - 00002b2a: Database Hash (read)

Service: 00001910-0000-1000-8000-00805f9b34fb (Proprietary/IP Support)
  - 00002b10: Data IN (notify) ← Empfängt Daten
  - 00002b11: Data OUT (write, write-without-response) ← Sendet Befehle
```

### 3. Protokoll-Analyse

**Erkenntnisse:**
- Das Gerät verwendet **NICHT** das klassische Tuya-BLE-Protokoll (FFF0/FFF1)
- Stattdessen nutzt es **Service 0x1910** mit standardisierten Characteristics
- Dies deutet auf ein **neueres Tuya-BLE-Protokoll** hin

**Bedeutung:**
- Direkte Kommunikation ohne Cloud möglich, ABER
- Verschlüsselung erfordert Device Credentials

---

## Nächste Schritte

### Option A: Tuya Cloud Integration (Empfohlen)

1. **Tuya IoT Developer Account erstellen:**
   - https://iot.tuya.com/
   - Kostenloses Konto anlegen

2. **Smart Life App mit Cloud verknüpfen:**
   - "Link Tuya App Account" im IoT-Portal
   - Steckdose in Smart Life App hinzufügen (falls noch nicht)

3. **Device Credentials extrahieren:**
   - Device ID
   - Local Key
   - UUID
   - Category (vermutlich "cz" für Socket)

4. **tuya-ble Library verwenden:**
   ```python
   from tuya_ble import TuyaBLE, TuyaDeviceInfo

   device_info = TuyaDeviceInfo(
       device_id="<device_id>",
       device_local_key="<local_key>",
       device_uuid="<uuid>",
       device_category="cz"
   )

   device = TuyaBLE(device_info, "18:DE:50:93:13:6D")
   await device.connect()
   await device.switch(True)  # Ein
   await device.switch(False) # Aus
   ```

### Option B: Reverse Engineering (Aufwändig)

1. BLE-Traffic mit Wireshark/nRF Connect mitschneiden
2. Protokoll analysieren
3. Eigene Implementierung schreiben

---

## Installierte Tools auf Raspberry Pi

```bash
# BLE Libraries
pip3 install --user --break-system-packages bleak tuya-ble pycryptodome tinytuya

# System Tools
sudo apt install bluetooth bluez bluez-tools
```

---

## Zusammenfassung

| Kriterium | Status |
|-----------|--------|
| BLE-Gerät erkannt | ✅ Ja |
| MAC-Adresse | ✅ 18:DE:50:93:13:6D |
| Verbindung möglich | ✅ Ja |
| Klassisches Tuya-BLE (FFF0) | ❌ Nein |
| Modernes Tuya-Protokoll | ✅ Ja (Service 0x1910) |
| Direkte Steuerung ohne Cloud | ⚠️ Möglich, erfordert Credentials |
| TinyTuya kompatibel | ❌ Nein (WiFi-only) |
| tuya-ble kompatibel | ✅ Ja (mit Cloud-Credentials) |

**Empfehlung:** Tuya IoT Cloud einrichten, um Device Credentials zu erhalten.
