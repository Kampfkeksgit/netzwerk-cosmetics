# NetzwerkCosmetics

Flügel und eigene Menüs für dein Minecraft-Netzwerk, **ohne Client-Mods**: Alles läuft über ein
Server-Resource-Pack, das der Spieler beim Joinen automatisch bekommt.

- **Flügel** (Engel, Dämon, Fee) als 3D-Modelle am Rücken, mit Flügelschlag-Animation
  (beim Fliegen/Elytra schneller)
- **Garderobe** (`/garderobe`) mit komplett eigenem Hintergrundbild und eigenen Icons
- **Netzwerkweit ohne Datenbank**: Das BungeeCord-Plugin speichert, wer welche Flügel trägt
- **Kein eigener Webserver nötig**: Das Pack liegt bei einem kostenlosen Host (z. B. mc-packs.net)

Für **Paper 26.3** (Java 25) und **BungeeCord**. Resource-Pack-Format 97 (26.3) ist abgedeckt.

## Installieren & Updaten per Git (Windows, cmd)

Die fertigen Dateien liegen immer im Ordner `dist/` dieses Repos, du musst nichts selbst bauen.

**Einmalig** ([Git für Windows](https://git-scm.com/download/win) muss installiert sein):

```bat
cd C:\Server
git clone https://github.com/Kampfkeksgit/netzwerk-cosmetics.git
```

Beim ersten Mal fragt Git nach deinem GitHub-Login, weil das Repo privat ist. Danach in
`C:\Server\netzwerk-cosmetics\update.bat` oben die Ordner deiner Server eintragen.

**Updaten:** Server stoppen, dann:

```bat
C:\Server\netzwerk-cosmetics\update.bat
```

Das Skript macht `git pull` und kopiert die Paper-JAR in alle eingetragenen Server und die
Bungee-JAR in den Proxy. Nur pullen, ohne zu kopieren, geht so:

```bat
cd C:\Server\netzwerk-cosmetics
git pull
```

## Dateien

In `dist/`:

| Datei | Wohin |
|---|---|
| `NetzwerkCosmetics-Paper.jar` | `plugins/` auf **jedem Paper-Server** (Lobby, Spielmodi) |
| `NetzwerkCosmetics-Bungee.jar` | `plugins/` auf dem **BungeeCord-Proxy** |
| `resourcepack.zip` | zu deinem Pack-Host hochladen |
| `resourcepack.sha1` | Prüfsumme des Packs (nur zur Kontrolle) |

## Einrichtung

1. **Pack hochladen:** `resourcepack.zip` z. B. auf <https://mc-packs.net> hochladen und den
   direkten Download-Link kopieren. Der Link muss ohne Login abrufbar sein.
2. **Plugins installieren:** Paper-JAR auf alle Server, Bungee-JAR auf den Proxy. Einmal starten und wieder stoppen.
3. **Config** auf **jedem** Paper-Server (`plugins/NetzwerkCosmetics/config.yml`):
   ```yaml
   resource-pack:
     mode: external
     external:
       url: "https://...dein-link.../resourcepack.zip"
   storage:
     type: bungee
   ```
   Überall dieselbe URL, dann lädt der Client das Pack beim Serverwechsel nicht neu.
4. **Rechte** vergeben, z. B. mit LuckPerms:
   ```
   /lp group vip permission set cosmetics.wings.angel true
   ```

**Wichtig bei Updates:** Ändert sich das Resource Pack (neue Flügel usw.), musst du die neue
`resourcepack.zip` hochladen, die URL aktualisieren **und** die neue Paper-JAR installieren. Der
SHA-1 wird aus der ZIP in der JAR berechnet und muss zur hochgeladenen Datei passen.

Solange keine URL eingetragen ist, sendet das Plugin kein Pack und kickt niemanden. Es steht dann
ein Fehler in der Konsole.

## Wie funktioniert das ohne Mods?

| Feature | Technik (Vanilla) |
|---|---|
| Flügel | Zwei `ItemDisplay`-Entities sitzen als Passagiere auf dem Spieler. Ihr Item hat die `item_model`-Komponente, das Modell kommt aus dem Resource Pack (`assets/cosmetics/items/wings/*`). Die Animation läuft über die Interpolation der Display-Entities, also flüssig auf dem Client. |
| Menü-Hintergrund | Der Inventar-Titel ist Text. Ein eigener Font (`font/gui.json`) macht aus dem Zeichen `` ein 176×222-Bild. Mit Leerzeichen negativer Breite (`font/space.json`) wird es genau über die Truhe geschoben (siehe `GuiFont.java`). |
| Menü-Icons | Normale Papier-Items mit `item_model`, dadurch eigene Texturen. |
| Speicher ohne DB | Paper fragt beim Join per Plugin-Message (`netzwerkcosmetics:sync`) beim Proxy nach. Der Proxy speichert alles in `plugins/NetzwerkCosmetics/selections.yml`. Nachrichten von Spielern auf diesem Kanal verwirft der Proxy. |

## Bauen

Nur nötig, wenn du selbst etwas am Code oder Pack änderst. Benötigt **Java 25**.

```bash
./gradlew build
```

Das aktualisiert `dist/`. Danach `dist/` mit committen, damit die Server es per `git pull` bekommen.

Grafiken ändern: PNGs/Modelle in `resourcepack/` ersetzen (z. B. mit Blockbench) und neu bauen.
Die Platzhalter-Grafiken kannst du mit `python3 tools/generate_assets.py` neu erzeugen (braucht Pillow).

## Befehle & Rechte

| Befehl | Recht | Beschreibung |
|---|---|---|
| `/garderobe` (`/wardrobe`, `/cosmetics`) | `cosmetics.use` | Garderobe öffnen |
| `/fluegel <id\|aus>` (`/wings`) | `cosmetics.use` | Flügel direkt an-/ablegen |
| `/cosmeticsadmin reload` | `cosmetics.admin` | Config neu laden |
| `/cosmeticsadmin pack [spieler]` | `cosmetics.admin` | Pack erneut senden |
| – | `cosmetics.wings.<id>` | Flügel freischalten (`cosmetics.wings.*` = alle) |

## Neue Flügel hinzufügen

1. Textur `resourcepack/assets/cosmetics/textures/item/wings/<id>.png` (32×32, Flügelwurzel links)
   und Icon `<id>_icon.png` (16×16) anlegen.
2. Modelle `models/item/wings/<id>_left.json`, `<id>_right.json`, `<id>_icon.json` und die
   Item-Definitionen in `items/wings/` anlegen (von `angel` kopieren und den Namen ändern).
3. Eintrag unter `wings:` in der `config.yml`, Permission in `plugin.yml`, neu bauen, Pack neu hochladen.

Eigene 3D-Modelle aus Blockbench funktionieren genauso: Die Flügelwurzel muss bei `[8, 8, 8]` liegen
(das ist der Drehpunkt für die Animation).

## Feintuning

Alle Werte unter `wing-settings` in der Config, wirksam mit `/cosmeticsadmin reload`:
`scale`, `offset-y`, `offset-z`, `rest-angle`, Schlag-Tempo usw. Zeigen die Flügel nach vorne statt
nach hinten, `invert-sweep: true` setzen.

## Stand der Tests

- Kompiliert gegen Paper-API 26.3 und BungeeCord-API ohne Warnungen.
- Auf einem echten Paper-26.3-Server gestartet: Plugin lädt, Speicher und Pack-Auslieferung funktionieren.
- Asset-Formate (Item-Definitionen, Fonts, Atlas) mit den Original-Dateien von 26.3 abgeglichen.
- **Noch nicht im Spiel mit echtem Client getestet:** Position/Richtung der Flügel, Ausrichtung des
  Menü-Hintergrunds und die Synchronisierung über BungeeCord.
