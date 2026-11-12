# CLAUDE.md – NetzwerkCosmetics

Minecraft-Netzwerk-Plugin: Flügel und Custom-UI **nur über ein Server-Resource-Pack**, ohne Client-Mods.
Zielplattform: **Paper 26.3 (Java 25)** hinter **BungeeCord**, ohne Datenbank. Der Nutzer spricht Deutsch:
Antworten, Ingame-Texte, Config-Kommentare und README auf Deutsch.

## Aufbau

```
paper/      Paper-Plugin (Flügel, Garderoben-GUI, Pack-Versand, Speicher)
bungee/     BungeeCord-Plugin (speichert Auswahl netzwerkweit in selections.yml)
resourcepack/   Resource Pack (wird GENERIERT, siehe unten – nicht von Hand pflegen,
                außer bewusst eigene Blockbench-Modelle)
tools/      generate_assets.py (Pack erzeugen), wings.py (Flügel-Modelle/Texturen),
            preview.py (Software-Renderer für Vorschaubilder), validator/ (Prüfung mit echtem Client-Code)
dist/       FERTIGE JARs + resourcepack.zip – wird committet, der Nutzer holt sie per `git pull`
```

## Befehle

```bash
./gradlew build                      # baut beide Plugins + resourcepack.zip, aktualisiert dist/
python3 tools/generate_assets.py     # erzeugt resourcepack/ neu (Pillow + numpy nötig)
python3 tools/preview.py angel demon # Vorschau -> build/preview/<id>.png (Rücken, schräg, Seite, vorne, Flügelschlag)
MC_CLIENT_JAR=... MC_LIBS=... tools/validate-pack.sh   # Pack mit den echten 26.3-Parsern prüfen
```

- Gradle braucht nur **ein JDK 25**. Keine Toolchains verwenden; das Bungee-Modul kompiliert per `options.release = 21`.
  (Toolchains haben beim Nutzer den Build gebrochen, weil kein JDK 21 installiert war.)
- Nach jeder Änderung an Code oder Pack: `./gradlew build` und **`dist/` mit committen**.
- Ändert sich das Pack, muss der Nutzer `dist/resourcepack.zip` neu hochladen (z. B. mc-packs.net) und die URL
  in der config.yml anpassen. Der SHA-1 wird aus der ZIP in der JAR berechnet und muss zur hochgeladenen Datei passen.
  Der Build ist reproduzierbar (gleiche Dateien = gleicher SHA-1).

## Validator einrichten (in einer frischen Cloud-Sitzung)

Braucht die 26.3-`client.jar` (piston-meta/piston-data.mojang.com), die Bibliotheken eines Paper-26.3-Servers
(`libraries/` nach dem ersten Start) plus `icu4j` und die LWJGL-Java-JARs (ohne Natives) – Versionen aus
der Version-JSON von Mojang, herunterladbar über `repo.papermc.io/repository/maven-public/`.
Der Validator registriert nur `ItemModels` + Item-Properties, **nicht** `ClientBootstrap` (das lädt Grafik-Natives).
Gegenprobe: Vanilla-Items/Fonts laufen bis auf Spezial-Renderer (Banner, Köpfe …) fehlerfrei durch.

## Fakten zu 26.3 (aus dem Spielcode geprüft, nicht raten)

- Resource-Pack-Format **97.1**. `pack.mcmeta` deckt 46–999 ab (`pack_format` + `supported_formats` + `min_format`/`max_format`).
- Modellelemente: `rotation` mit `"origin"` und **entweder** `"axis"`/`"angle"` **oder** `"x"`,`"y"`,`"z"` (beliebige Winkel).
  Reihenfolge: `Matrix4f.rotationZYX(z, y, x)` = Rz·Ry·Rx (X wird zuerst angewendet).
- `light_emission` (0–15) pro Element -> leuchtende Teile. `shade` gibt es nicht mehr, dafür `shade_direction_override`.
- `from`/`to` müssen **vor der Drehung** in −16..32 liegen (lange Quader am äußeren Ende verankern, siehe `ModelBuilder.segment`).
- Item-Texturen unter `textures/item/**` landen im Item-Atlas (`atlases/items.json`, auch für eigene Namespaces).
- Modell-Parser: `net.minecraft.client.resources.model.cuboid.CuboidModel` (heißt nicht mehr BlockModel).
- **ItemDisplay dreht das Item um 180° um Y** (`ItemDisplayRenderer.submitInner`), NACH der Display-Transformation.
  Folge: Modell +X zeigt im Entity-Raum nach −X; **höheres Modell-Z = beim Spieler außen/hinten** (vom Rücken sichtbar).

## Flügel-System

- Jeder Flügel = 2 `ItemDisplay`-Passagiere auf dem Spieler (`WingInstance`), Item mit `item_model`.
  Drehpunkt/Flügelwurzel im Modell: **(8, 8, 8)**. Der rechte Flügel ist automatisch gespiegelt (`wings.mirror`).
- Animation: Transformation um Y, Client-Interpolation. Start-Delay `-1 -> 0` im selben Tick, damit er sicher gesendet wird.
- Teleport wirft Passagiere ab -> `hideTemporarily` + Neuaufbau im Tick.
- Neue Flügel: Stil in `tools/wings.py` (`WINGS`) eintragen, `generate_assets.py` laufen lassen, Vorschau ansehen,
  validieren, Eintrag in `paper/src/main/resources/config.yml` + Permission in `plugin.yml`.
- Designs sind **eigene Entwürfe im Anime-Stil**. Keine Flügel bestimmter Anime-Figuren nachbauen.

## Netzwerk / Speicher

- `storage.type: bungee` (Standard): Plugin-Messaging auf Kanal `netzwerkcosmetics:sync`, Protokoll-Byte `1`.
  Paper fragt nach dem Join mit `GET` (mit Wiederholungen, der Kanal ist evtl. noch nicht registriert), meldet `SET`.
  Der Proxy verwirft Nachrichten vom Client auf dem Kanal. Ändert sich das Format: Protokoll-Byte erhöhen, beide Seiten anpassen.
- Alternativ `sqlite` (Einzelserver) oder `mysql`.

## Custom-UI

Garderoben-Hintergrund = Font-Glyph `` (176×222, ascent 13) im Inventartitel, verschoben mit Space-Font
(`cosmetics:space`, Zeichen U+F000.. negativ / U+F100.. positiv, Zweierpotenzen). Glyph muss weiß eingefärbt sein.
Layout der Slots muss zu `textures/gui/wardrobe.png` passen (`WardrobeMenu`).

## Testen – was geht und was nicht

- Plugin-Start kann auf einem echten Paper-26.3-Server geprüft werden (offline-mode, Whitelist aus).
- Ein echter 26.3-Client ist in der Cloud **nicht** verfügbar (minecraft-protocol kann nur bis 26.1).
  Optik im Spiel daher immer mit `tools/preview.py` vorab prüfen und den Nutzer um Screenshots bitten.
- Blockbench-MCP läuft lokal beim Nutzer – nur in einer lokalen Sitzung nutzbar, nicht in der Cloud.

## Konventionen

- Java: Strings/Kommentare ohne Umlaute (ae/oe/ue), Texte für Spieler über MiniMessage in der config.yml.
- Keine Modell-/Versions-IDs in Commits. Commits auf Deutsch, kurz und beschreibend.
