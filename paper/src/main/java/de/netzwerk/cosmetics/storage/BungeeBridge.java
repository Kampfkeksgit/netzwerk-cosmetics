package de.netzwerk.cosmetics.storage;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiConsumer;
import java.util.logging.Level;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.plugin.messaging.PluginMessageListener;
import org.jetbrains.annotations.NotNull;

/**
 * Spricht per Plugin-Messaging mit dem NetzwerkCosmetics-Plugin auf dem BungeeCord-Proxy.
 * Dort liegt die Auswahl aller Spieler (selections.yml) - eine Datenbank ist nicht noetig.
 *
 * <p>Plugin-Messages laufen ueber die Verbindung eines Spielers. Deshalb fragt der Server erst
 * nach dem Join nach ({@code GET}) und wiederholt die Anfrage, falls der Kanal noch nicht
 * bereit war.
 */
final class BungeeBridge implements PluginMessageListener {

    static final String CHANNEL = "netzwerkcosmetics:sync";
    private static final int PROTOCOL = 1;
    private static final int RETRY_TICKS = 40;
    private static final int MAX_TRIES = 5;

    private final CosmeticsPlugin plugin;
    private final BiConsumer<Player, Map<String, String>> onData;
    private final Set<UUID> pending = ConcurrentHashMap.newKeySet();

    BungeeBridge(CosmeticsPlugin plugin, BiConsumer<Player, Map<String, String>> onData) {
        this.plugin = plugin;
        this.onData = onData;
    }

    void register() {
        Bukkit.getMessenger().registerOutgoingPluginChannel(plugin, CHANNEL);
        Bukkit.getMessenger().registerIncomingPluginChannel(plugin, CHANNEL, this);
    }

    void unregister() {
        Bukkit.getMessenger().unregisterOutgoingPluginChannel(plugin, CHANNEL);
        Bukkit.getMessenger().unregisterIncomingPluginChannel(plugin, CHANNEL, this);
    }

    /** Fragt die gespeicherte Auswahl beim Proxy an (mit Wiederholungen). */
    void request(Player player) {
        pending.add(player.getUniqueId());
        attempt(player, 1);
    }

    boolean isPending(UUID uuid) {
        return pending.contains(uuid);
    }

    void cancel(UUID uuid) {
        pending.remove(uuid);
    }

    private void attempt(Player player, int tryNumber) {
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline() || !pending.contains(player.getUniqueId())) {
                return;
            }
            if (tryNumber > MAX_TRIES) {
                pending.remove(player.getUniqueId());
                plugin.getLogger().warning("Keine Antwort vom BungeeCord-Proxy fuer " + player.getName()
                        + ". Ist NetzwerkCosmetics auch auf dem Proxy installiert?");
                return;
            }
            send(player, out -> out.writeUTF("GET"));
            attempt(player, tryNumber + 1);
        }, tryNumber == 1 ? 2L : RETRY_TICKS);
    }

    void sendSet(Player player, String slot, String value) {
        send(player, out -> {
            out.writeUTF("SET");
            out.writeUTF(slot);
            out.writeUTF(value == null ? "" : value);
        });
    }

    private void send(Player player, IoWriter writer) {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeByte(PROTOCOL);
            writer.write(out);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        player.sendPluginMessage(plugin, CHANNEL, bytes.toByteArray());
    }

    @Override
    public void onPluginMessageReceived(@NotNull String channel, @NotNull Player player, byte @NotNull [] message) {
        if (!CHANNEL.equals(channel)) {
            return;
        }
        try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(message))) {
            if (in.readByte() != PROTOCOL || !"DATA".equals(in.readUTF())) {
                return;
            }
            int count = in.readInt();
            Map<String, String> data = new HashMap<>();
            for (int i = 0; i < count; i++) {
                data.put(in.readUTF(), in.readUTF());
            }
            if (pending.remove(player.getUniqueId())) {
                onData.accept(player, data);
            }
        } catch (IOException e) {
            plugin.getLogger().log(Level.WARNING, "Fehlerhafte Antwort vom Proxy fuer " + player.getName(), e);
        }
    }

    @FunctionalInterface
    private interface IoWriter {
        void write(DataOutputStream out) throws IOException;
    }
}
