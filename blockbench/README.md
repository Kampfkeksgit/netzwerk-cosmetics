# Blockbench-Projekt

`wings.bbmodel` enthaelt **alle Fluegel in einem Projekt**. Jeder Fluegel ist eine Gruppe im Outliner,
darunter Untergruppen je Lage (z. B. `primary`, `covert`, `bone`, `membrane`). Texturen sind eingebettet.

- Alle Fluegel liegen an derselben Stelle (Wurzel bei 8,8,8). Sichtbar ist nur der erste -
  die anderen blendest du im Outliner mit dem Auge an der jeweiligen Gruppe ein.
- Nur die linke Seite: die rechte entsteht immer per Spiegelung (`wings.mirror` in `tools/wings.py`).

## Wichtig: Quelle ist `tools/wings.py`

Das Projekt ist eine **Ansicht** der generierten Modelle und wird von
`python3 tools/generate_assets.py` jedes Mal neu geschrieben. Aenderungen, die nur hier im Projekt
gemacht werden, gehen dabei verloren.

- **Ausprobieren / anschauen:** Projekt oeffnen, frei bearbeiten (am besten unter anderem Namen speichern).
- **Dauerhaft uebernehmen:** die Aenderung in `tools/wings.py` nachziehen, dann
  `generate_assets.py`, `preview.py`, `gradlew.bat build`.

Regeln fuer die Geometrie stehen in der `CLAUDE.md` (Wurzel bei (8,8,8), `from`/`to` in -16..32,
hoeheres Z = aussen, `light_emission` fuer Leuchtteile).
