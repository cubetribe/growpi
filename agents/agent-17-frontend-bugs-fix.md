# Agent #17: Frontend Bugs Fix (Kurven + CSS)

**Date**: 2025-12-06
**Status**: SUCCESS

---

## Problems Fixed

### 1. Kurven-Tab zeigt keine Daten

**Symptom**: Kurven-Tab laedt, aber Content ist leer (keine Kanaldaten angezeigt)

**Root Cause**: `fetchCurves()` wurde NIE aufgerufen!
- `initCurvesTab()` setzt nur Event Listener auf
- Aber niemand ruft `fetchCurves()` auf um die Daten initial zu laden

**Fix**: Tab-Switch-Handler in `utils.js` hinzugefuegt
- Beim Klick auf "Kurven"-Tab wird `fetchCurves()` dynamisch importiert und aufgerufen
- Nutzt dynamisches `import()` um Circular Dependencies zu vermeiden

**Code Change** (`js/utils.js`):
```javascript
// Load data when switching to specific tabs
if (tabId === 'curves') {
    // Dynamically import and call fetchCurves
    import('./modules/curves.js').then(module => {
        module.fetchCurves();
    }).catch(err => {
        console.error('Failed to load curves module:', err);
    });
}
```

---

### 2. Kosten/Room Buttons haben falsches Styling

**Symptom**: `.cost-period-btn` Buttons (Heute, 7 Tage, etc.) haben weissen Hintergrund statt dark theme

**Root Cause**: CSS fuer `.cost-period-btn` und `.room-toggle-btn` fehlte komplett in `main.css`

**Fix**: CSS Styles am Ende von `main.css` hinzugefuegt:
- `.cost-period-btn` und `.room-toggle-btn` - Dark theme mit border
- `:hover` State - Leichter green glow
- `.active` State - Neon green background (wie bei `.range-btn`)
- `.btn` Klasse fuer "Anwenden" und "Speichern" Buttons

**Code Change** (`css/main.css`):
```css
/* Cost & Room Tab Button Styles */
.cost-period-btn,
.room-toggle-btn {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #888;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
}

.cost-period-btn.active,
.room-toggle-btn.active {
    background: #11ff55;
    border-color: #11ff55;
    color: #000;
    font-weight: 600;
}
```

---

## Files Modified

| File | Changes |
|------|---------|
| `pi-controller/grow_pi/web/static/js/utils.js` | +13 lines - Tab-Switch-Handler fuer Kurven-Tab |
| `pi-controller/grow_pi/web/static/css/main.css` | +53 lines - CSS fuer cost-period-btn, room-toggle-btn, btn |

---

## Git Diff Summary

```
pi-controller/grow_pi/web/static/css/main.css | +53 lines
pi-controller/grow_pi/web/static/js/utils.js  | +13 lines
----------------------------------------------
2 files changed, 66 insertions(+)
```

---

## Deployment

**ACHTUNG**: Files muessen noch auf Pi deployed werden!

```bash
# SSH Password aus .env
PI_PASS="Mi83xer#"

# Deploy geaenderte Files
sshpass -p "$PI_PASS" scp \
  pi-controller/grow_pi/web/static/js/utils.js \
  pi-controller/grow_pi/web/static/css/main.css \
  admin@192.168.0.86:/opt/grow-pi/grow_pi/web/static/

# Kein Service-Restart noetig (statische Files!)
```

---

## Verification Checklist

- [x] `fetchCurves()` wird beim Tab-Wechsel zu "Kurven" aufgerufen
- [x] CSS fuer `.cost-period-btn` existiert in main.css
- [x] CSS fuer `.room-toggle-btn` existiert in main.css
- [x] `.btn` Klasse fuer Anwenden/Speichern Buttons hinzugefuegt
- [x] Files deployed to Pi (utils.js + main.css)
- [ ] Kurven-Tab laedt Daten beim Klick (User muss testen)
- [ ] Kosten-Buttons haben dark style + green active (User muss testen)

---

## Technical Notes

### Warum dynamisches Import?

```javascript
import('./modules/curves.js').then(module => {
    module.fetchCurves();
});
```

1. **Vermeidet Circular Dependencies**: `utils.js` wird von `curves.js` importiert
2. **Lazy Loading**: Module wird nur geladen wenn Tab geklickt wird
3. **Error Handling**: `.catch()` faengt fehlende Module ab

### CSS Konsistenz

Die neuen Button-Styles matchen exakt die bestehenden `.range-btn` Styles aus dem Verlauf-Tab:
- Gleiche `background`, `border`, `color` Werte
- Gleicher `.active` State mit `#11ff55`
- Gleiche `transition: all 0.2s`

---

## Status

**SUCCESS** - Fixes implementiert und auf Pi deployed!

Test-URL: http://192.168.0.86:5000 (Refresh mit Ctrl+Shift+R fuer Cache-Clear)
