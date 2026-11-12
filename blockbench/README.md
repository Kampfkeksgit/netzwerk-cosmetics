# Blockbench-Projekte

Ein Projekt pro Fluegel (`<id>_left.bbmodel`), Texturen eingebettet, Elemente nach Lagen gruppiert.
Nur die linke Seite: die rechte entsteht immer per Spiegelung (`wings.mirror` in `tools/wings.py`).

## Wichtig: Quelle ist `tools/wings.py`

Diese Projekte sind eine **Ansicht** der generierten Modelle, nicht die Quelle.
`python3 tools/generate_assets.py` baut `models/item/wings` und `textures/item/wings` komplett
neu aus `wings.py` - eine Aenderung, die nur hier im Projekt oder nur in der JSON steht, geht dabei verloren.

## Aenderungen

- **Ausprobieren / anschauen:** Projekt oeffnen, frei bearbeiten.
- **Dauerhaft uebernehmen:** die Aenderung in `tools/wings.py` nachziehen, dann
  `generate_assets.py`, `preview.py`, `gradlew.bat build`.
- Nach einer Aenderung an `wings.py` sind die Projekte hier veraltet und muessen neu erzeugt werden.

Regeln fuer die Geometrie stehen in der `CLAUDE.md` (Wurzel bei (8,8,8), `from`/`to` in -16..32,
hoeheres Z = aussen, `light_emission` fuer Leuchtteile).
