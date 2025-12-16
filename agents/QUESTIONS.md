# OFFENE FRAGEN

**Letzte Aktualisierung**: 2025-12-07

---

## Q1: Bug #8/#9/#10 - Deployment-Status unklar

**Kontext**:
Die Fixes für Bug #8 (Status-Desync), Bug #9 (Plug Verification) und Bug #10 (Manual Override) sind **lokal im Repository vorhanden**.

**Frage an User**:
Wurde v6.14.0+ mit diesen Fixes bereits auf den Raspberry Pi deployed?

**Optionen**:
- A) Ja, deployed und läuft
- B) Nein, noch nicht deployed - bitte jetzt deployen
- C) Nicht sicher - bitte prüfen

**Relevanz**:
Wenn bereits deployed, können wir direkt zur Validierung übergehen.
Wenn nicht deployed, müssen wir erst deployen und dann validieren.

---

## Q2: Bug #11 - Konkrete Symptome

**Kontext**:
Die Roadmap beschreibt Bug #11 (Datalog/History Problem) nur vage:
- Console zeigt `[History] Loading data for 24 hours (downsampled)`
- "Unbekanntes Problem mit der History-Seite"

**Frage an User**:
Was genau ist das Problem?

**Optionen**:
- A) Chart wird nicht angezeigt (leer/blank)
- B) Daten sind falsch/unvollständig
- C) Performance-Problem (langsam)
- D) UI-Problem (Layout/Styling)
- E) Console-Logs sind nur zur Info, kein echtes Problem

**Relevanz**:
Ohne klare Symptombeschreibung können wir das Problem nicht reproduzieren oder debuggen.

---

## Q3: Zeitschaltung (Bug #2) - UI-Existenz

**Kontext**:
Bug #2 beschreibt "Zeitschaltung/Override testen", aber es ist unklar ob die UI-Komponente existiert.

**Frage an User**:
Gibt es bereits eine UI zum Anlegen von Zeitfenstern für den Entfeuchter?

**Optionen**:
- A) Ja, im Room-Tab
- B) Ja, an anderer Stelle
- C) Nein, muss noch implementiert werden
- D) Nicht sicher

**Relevanz**:
Wenn keine UI existiert, können wir Bug #2 nicht testen und er ist eigentlich ein Feature-Request.

---
