package de.netzwerk.cosmetics.bungee;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Level;
import net.md_5.bungee.api.connection.ProxiedPlayer;
import net.md_5.bungee.api.connection.Server;
import net.md_5.bungee.api.event.PluginMessageEvent;
import net.md_5.bungee.api.plugin.Listener;
import net.md_5.bungee.api.plugin.Plugin;
import net.md_5.bungee.config.Configuration;
import net.md_5.bungee.config.ConfigurationProvider;
import net.md_5.bungee.config.YamlConfiguration;
import net.md_5.bungee.event.EventHandler;

/**
 * Netzwerkweiter Speicher ohne Datenbank.
 *
 * <p>Die Paper-Server fragen beim Join per Plugin-Message nach der Auswahl eines Spielers
 * ({@code GET}) und melden Aenderungen ({@code SET}). Der Proxy haelt alles im Speicher und
 * schreibt es regelmaessig nach {@code plugins/NetzwerkCosmetics/selections.yml}.
 *
 * <p>Nachrichten vom Client auf diesem Kanal werden verworfen - ein Spieler kann sich also
 * nicht selbst Kosmetik "einschmuggeln". Freigeschaltet wird ohnehin per Permission auf dem
 * Paper-Server.
 */
public final class CosmeticsBungee extends Plugin implements Listener {

    /** Muss mit dem Kanal im Paper-Plugin uebereinstimmen. */
    public static final String CHANNEL = "netzwerkcosmetics:sync";
    private static final int PROTOCOL = 1;

    private final Map<UUID, Map<String, String>> selections = new ConcurrentHashMap<>();
    private final AtomicBoolean dirty = new AtomicBoolean();
    private File file;

    @Override
    public void onEnable() {
        file = new File(getDataFolder(), "selections.yml");
        load();
        getProxy().registerChannel(CHANNEL);
        getProxy().getPluginManager().registerListener(this, this);
        getProxy().getScheduler().schedule(this, this::saveIfDirty, 30, 30, TimeUnit.SECONDS);
        getLogger().info(selections.size() + " Spieler-Auswahlen geladen.");
    }

    @Override
    public void onDisable() {
        dirty.set(true);
        saveIfDirty();
        getProxy().unregisterChannel(CHANNEL);
    }

    @EventHandler
    public void onPluginMessage(PluginMessageEvent event) {
        if (!CHANNEL.equals(event.getTag())) {
            return;
        }
        // Niemals an den Client weiterleiten und niemals Client-Nachrichten annehmen
        event.setCancelled(true);
        if (!(event.getSender() instanceof Server server) || !(event.getReceiver() instanceof ProxiedPlayer player)) {
            return;
        }
        UUID uuid = player.getUniqueId();
        try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(event.getData()))) {
            if (in.readByte() != PROTOCOL) {
                getLogger().warning("Unbekannte Protokollversion von " + server.getInfo().getName()
                        + " - sind Paper- und Bungee-Plugin gleich aktuell?");
                return;
            }
            String op = in.readUTF();
            switch (op) {
                case "GET" -> server.sendData(CHANNEL, encodeData(uuid));
                case "SET" -> {
                    String slot = in.readUTF();
                    String value = in.readUTF();
                    Map<String, String> data = selections.computeIfAbsent(uuid, k -> new ConcurrentHashMap<>());
                    if (value.isEmpty()) {
                        data.remove(slot);
                        if (data.isEmpty()) {
                            selections.remove(uuid);
                        }
                    } else {
                        data.put(slot, value);
                    }
                    dirty.set(true);
                }
                default -> getLogger().warning("Unbekannte Nachricht '" + op + "' von " + server.getInfo().getName());
            }
        } catch (IOException e) {
            getLogger().log(Level.WARNING, "Fehlerhafte Plugin-Message von " + server.getInfo().getName(), e);
        }
    }

    private byte[] encodeData(UUID uuid) throws IOException {
        Map<String, String> data = selections.getOrDefault(uuid, Map.of());
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeByte(PROTOCOL);
            out.writeUTF("DATA");
            Map<String, String> copy = Map.copyOf(data);
            out.writeInt(copy.size());
            for (Map.Entry<String, String> e : copy.entrySet()) {
                out.writeUTF(e.getKey());
                out.writeUTF(e.getValue());
            }
        }
        return bytes.toByteArray();
    }

    // ------------------------------------------------------------------ Datei

    private void load() {
        if (!file.exists()) {
            return;
        }
        try {
            Configuration root = ConfigurationProvider.getProvider(YamlConfiguration.class).load(file);
            Configuration players = root.getSection("players");
            for (String key : players.getKeys()) {
                UUID uuid;
                try {
                    uuid = UUID.fromString(key);
                } catch (IllegalArgumentException e) {
                    continue;
                }
                Configuration section = players.getSection(key);
                Map<String, String> data = new ConcurrentHashMap<>();
                for (String slot : section.getKeys()) {
                    String value = section.getString(slot, "");
                    if (!value.isEmpty()) {
                        data.put(slot, value);
                    }
                }
                if (!data.isEmpty()) {
                    selections.put(uuid, data);
                }
            }
        } catch (IOException e) {
            getLogger().log(Level.SEVERE, "selections.yml konnte nicht gelesen werden", e);
        }
    }

    private synchronized void saveIfDirty() {
        if (!dirty.getAndSet(false)) {
            return;
        }
        Configuration root = new Configuration();
        selections.forEach((uuid, data) -> data.forEach((slot, value) ->
                root.set("players." + uuid + "." + slot, value)));
        try {
            Files.createDirectories(getDataFolder().toPath());
            File tmp = new File(getDataFolder(), "selections.yml.tmp");
            ConfigurationProvider.getProvider(YamlConfiguration.class).save(root, tmp);
            Files.move(tmp.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            dirty.set(true); // beim naechsten Mal erneut versuchen
            getLogger().log(Level.SEVERE, "selections.yml konnte nicht gespeichert werden", e);
        }
    }
}
