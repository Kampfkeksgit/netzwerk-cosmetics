#!/bin/sh
# Prueft resourcepack/ mit den Parsern des echten Minecraft-Clients.
#   MC_CLIENT_JAR = Pfad zur client.jar der Ziel-Version (z.B. 26.3)
#   MC_LIBS       = Ordner mit den Bibliotheken (z.B. libraries/ eines Paper-Servers)
set -e
cd "$(dirname "$0")/.."
: "${MC_CLIENT_JAR:?MC_CLIENT_JAR setzen}"
: "${MC_LIBS:?MC_LIBS setzen}"
CP="$MC_CLIENT_JAR:$(find "$MC_LIBS" -name '*.jar' | tr '\n' ':')"
exec java -cp "$CP" tools/validator/PackValidator.java resourcepack
