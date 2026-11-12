# NetzwerkCosmetics

Flügel und eigene Menüs für dein Minecraft-Netzwerk, **ohne Client-Mods**: Alles läuft über ein
Server-Resource-Pack, das der Spieler beim Joinen automatisch bekommt.

- **Flügel** (Engel, Dämon, Fee) als 3D-Modelle am Rücken, mit Flügelschlag-Animation
  (beim Fliegen/Elytra schneller)
- **Garderobe** (`/garderobe`) mit komplett eigenem Hintergrundbild und eigenen Icons
- **Netzwerkweit** über MySQL: Spieler haben ihre Flügel auf jedem Server
- **Resource Pack Hosting** direkt im Plugin (oder extern über Webserver/CDN)

Kompiliert gegen die Paper-API 1.21.11 (Java 21), gedacht für Paper/Purpur ab 1.21.4.

## Wie funktioniert das ohne Mods?

| Feature | Technik (Vanilla) |
|---|---|
| Flügel | Zwei `ItemDisplay`-Entities sitzen als Passagiere auf dem Spieler. Ihr Item hat die `item_model`-Komponente → das Modell kommt aus dem Resource Pack (`assets/cosmetics/items/wings/*`). Die Animation läuft über die Interpolation der Display-Entities, also flüssig auf dem Client. |
| Menü-Hintergrund | Der Inventar-Titel ist Text. Ein eigener Font (`font/gui.json`) macht aus dem Zeichen `` ein 176×222-Bild. Mit Leerzeichen mit negativer Breite (`font/space.json`) wird es genau über die Truhe geschoben (siehe `GuiFont.java`). |
| Menü-Icons | Normale Papier-Items mit `item_model` → eigene Texturen. |

## Bauen

```bash
./gradlew build
```

Ergebnis:
- `build/libs/NetzwerkCosmetics-1.0.0.jar` → in `plugins/` legen (das Resource Pack ist darin enthalten)
- `build/resourcepack.zip` → falls du das Pack extern hosten willst

Grafiken ändern: PNGs/Modelle in `resourcepack/` ersetzen (z. B. mit Blockbench) und neu bauen.
Die Platzhalter-Grafiken kannst du mit `python3 tools/generate_assets.py` neu erzeugen (braucht Pillow).

## Einrichtung

1. JAR in `plugins/` legen, Server starten, stoppen.
2. In `plugins/NetzwerkCosmetics/config.yml`:
   - `resource-pack.internal.public-url` auf deine öffentliche IP/Domain setzen und Port `8085` freigeben,
     **oder** `mode: external` und die URL deines Webservers eintragen.
   - Für das Netzwerk: `storage.type: mysql` + Zugangsdaten auf **allen** Servern gleich.
3. Rechte vergeben, z. B. mit LuckPerms:
   ```
   /lp group vip permission set cosmetics.wings.angel true
   ```

### Netzwerk (Velocity/BungeeCord)

- Plugin auf jeden Backend-Server (Lobby, Spielmodi) legen, dort wo Flügel/Menüs gebraucht werden.
- **Alle Server müssen dieselbe Pack-URL senden.** Empfehlung: einen Server mit `mode: internal` hosten
  lassen (oder einen Webserver/CDN) und auf allen anderen `mode: external` mit genau dieser URL. Bei gleicher
  URL + gleichem SHA-1 lädt der Client das Pack beim Serverwechsel nicht neu.
- Backend-Server hinter dem Proxy sind oft nicht öffentlich erreichbar, dann unbedingt `external` verwenden.

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
   Item-Definitionen in `items/wings/` anlegen (einfach von `angel` kopieren und den Namen ändern).
3. Eintrag unter `wings:` in der `config.yml`, neu bauen, fertig.

Eigene 3D-Modelle aus Blockbench funktionieren genauso: Die Flügelwurzel muss bei `[8, 8, 8]` liegen
(das ist der Drehpunkt für die Animation).

## Feintuning

Alle Werte unter `wing-settings` in der Config, wirksam mit `/cosmeticsadmin reload`:
`scale`, `offset-y`, `offset-z`, `rest-angle`, Schlag-Tempo usw. Sollten die Flügel nach vorne statt
nach hinten zeigen, `invert-sweep: true` setzen.
