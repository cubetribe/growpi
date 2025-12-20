# SSH Diagnose Bericht - Raspberry Pi GrowPi
**Datum:** 2025-12-20
**Target:** 192.168.0.86 (admin@growpi)
**Status:** ❌ SSH-Verbindung fehlgeschlagen

---

## Zusammenfassung

**KRITISCHES PROBLEM:** SSH-Authentifizierung schlägt fehl. Alle Diagnosebefehle konnten nicht ausgeführt werden.

---

## 1. Fehlerdetails

### Authentifizierungsfehler
```
Permission denied, please try again.
Permission denied, please try again.
admin@192.168.0.86: Permission denied (publickey,password).
```

**Ursache:**
- SSH-Client sendet kein Passwort automatisch
- Keine SSH-Key-Authentifizierung konfiguriert
- Passwort-Authentifizierung erfordert interaktive Eingabe

### Connection Reset Fehler (nach mehreren Versuchen)
```
kex_exchange_identification: read: Connection reset by peer
Connection reset by 192.168.0.86 port 22
```

**Ursache:**
- Raspberry Pi hat möglicherweise Fail2Ban aktiviert
- Zu viele fehlgeschlagene Login-Versuche
- SSH-Server blockt temporär die IP

---

## 2. Nicht ausgeführte Diagnosebefehle

Folgende Befehle konnten **NICHT** ausgeführt werden:

❌ `sudo systemctl status grow-pi`
❌ `sudo journalctl -u grow-pi -n 100 --no-pager`
❌ `gpio readall`
❌ `sudo lsof /dev/gpiomem`
❌ `ps aux | grep python`
❌ `free -h`
❌ `cat /sys/class/thermal/thermal_zone0/temp`
❌ `df -h /`

---

## 3. Mögliche Ursachen für SSH-Fehler

### Option A: Fehlende SSH-Konfiguration
- Passwort ist in `.env` file, aber nicht in SSH-Config
- SSH-Client kann nicht automatisch Passwort übergeben

### Option B: SSH-Key-Authentifizierung erforderlich
- Raspberry Pi akzeptiert nur Public-Key-Auth
- Password-Auth ist deaktiviert in `/etc/ssh/sshd_config`

### Option C: Fail2Ban aktiv
- Nach mehreren fehlgeschlagenen Versuchen IP geblockt
- Temporäre Sperre (meist 10-30 Minuten)

---

## 4. Empfohlene Lösungsschritte

### Sofortmaßnahme: SSH mit Password-Prompt
```bash
# Interaktive SSH-Session (manuelle Passworteingabe)
ssh admin@192.168.0.86

# Dann manuell Befehle ausführen:
sudo systemctl status grow-pi
sudo journalctl -u grow-pi -n 100 --no-pager
```

### Lösung A: SSH-Key einrichten (empfohlen)
```bash
# 1. SSH-Key generieren (falls noch nicht vorhanden)
ssh-keygen -t ed25519 -C "growpi-diagnosis"

# 2. Public Key auf Pi kopieren
ssh-copy-id admin@192.168.0.86

# 3. Testen
ssh admin@192.168.0.86 "echo 'SSH Key funktioniert'"
```

### Lösung B: sshpass verwenden (unsicher, nur für Diagnose)
```bash
# ACHTUNG: Passwort im Klartext!
brew install sshpass  # macOS
sshpass -p 'PASSWORT' ssh admin@192.168.0.86 "sudo systemctl status grow-pi"
```

### Lösung C: SSH-Config mit Password-Helper
```bash
# In ~/.ssh/config ergänzen:
Host growpi
    HostName 192.168.0.86
    User admin
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
```

---

## 5. Fail2Ban Status prüfen (falls Zugang wiederhergestellt)

```bash
# Auf dem Pi ausführen:
sudo fail2ban-client status sshd
sudo fail2ban-client set sshd unbanip $(curl -s ifconfig.me)
```

---

## 6. Nächste Schritte

### PRIORITÄT 1: SSH-Zugang wiederherstellen
1. User muss **manuell** SSH-Passwort eingeben
2. Oder SSH-Key-Authentifizierung einrichten

### PRIORITÄT 2: Diagnose durchführen (nach SSH-Fix)
Sobald SSH funktioniert, erneut ausführen:
```bash
# Service-Status
sudo systemctl status grow-pi

# Logs checken
sudo journalctl -u grow-pi -n 100 --no-pager | grep -i error

# GPIO prüfen
gpio readall

# Prozesse
ps aux | grep python
```

### PRIORITÄT 3: Langfristige Lösung
- SSH-Key-Authentifizierung permanent einrichten
- Fail2Ban Whitelist für Entwickler-IP
- Dokumentation der SSH-Credentials aktualisieren

---

## 7. Technische Details

### SSH-Client-Verhalten (macOS)
- `ssh` command versucht automatisch:
  1. SSH-Keys aus `~/.ssh/`
  2. SSH-Agent keys
  3. Nur bei Fehler: Password-Prompt (interaktiv)

### Problem mit automatisierten Scripts
- Bash-Tool kann nicht interaktiv Passwort eingeben
- Lösung: SSH-Key ODER sshpass (unsicher)

---

## 8. Offene Fragen an User

1. **Ist das SSH-Passwort für admin@192.168.0.86 korrekt?**
2. **Ist ein SSH-Key bereits auf dem Pi hinterlegt?**
3. **Ist Fail2Ban auf dem Pi aktiv?**
4. **Soll ich SSH-Key-Authentifizierung einrichten? (empfohlen)**

---

## Status: BLOCKIERT

**Blocker:** SSH-Authentifizierung fehlgeschlagen
**Benötigt:** User-Interaktion für SSH-Zugang

**Diagnose kann fortgesetzt werden, sobald:**
- SSH-Key eingerichtet ist ODER
- User manuell SSH-Befehle ausführt ODER
- sshpass mit Passwort aus `.env` verwendet wird

---

**Erstellt von:** Claude Code Diagnose-Agent
**Nächste Aktualisierung:** Nach SSH-Fix
