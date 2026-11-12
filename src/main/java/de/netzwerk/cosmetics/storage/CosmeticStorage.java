package de.netzwerk.cosmetics.storage;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import org.bukkit.configuration.ConfigurationSection;

/**
 * Speichert, welche Kosmetik ein Spieler pro Slot traegt.
 *
 * <p>Mit {@code storage.type: mysql} teilen sich alle Server des Netzwerks dieselbe Tabelle:
 * Der Spieler hat seine Fluegel auf jedem Server. Geladen wird in
 * {@code AsyncPlayerPreLoginEvent} (also bevor der Spieler den Server betritt),
 * gespeichert sofort bei jeder Aenderung auf einem eigenen Thread.
 */
public final class CosmeticStorage {

    private final CosmeticsPlugin plugin;
    private final Map<UUID, Map<String, String>> cache = new ConcurrentHashMap<>();
    private final ExecutorService executor = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "NetzwerkCosmetics-DB");
        t.setDaemon(true);
        return t;
    });

    private boolean mysql;
    private String url;
    private String user;
    private String password;
    private Connection connection;

    public CosmeticStorage(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    public void init() throws SQLException {
        ConfigurationSection c = plugin.getConfig().getConfigurationSection("storage");
        String type = c == null ? "sqlite" : c.getString("type", "sqlite");
        mysql = "mysql".equalsIgnoreCase(type) || "mariadb".equalsIgnoreCase(type);
        if (mysql) {
            ConfigurationSection m = c.getConfigurationSection("mysql");
            if (m == null) {
                throw new SQLException("storage.mysql fehlt in der config.yml");
            }
            url = "jdbc:mysql://" + m.getString("host", "localhost") + ":" + m.getInt("port", 3306)
                    + "/" + m.getString("database", "cosmetics") + "?" + m.getString("params", "");
            user = m.getString("user", "root");
            password = m.getString("password", "");
        } else {
            File file = new File(plugin.getDataFolder(), "cosmetics.db");
            url = "jdbc:sqlite:" + file.getAbsolutePath();
        }
        try (Statement st = connection().createStatement()) {
            st.executeUpdate("CREATE TABLE IF NOT EXISTS cosmetic_selection ("
                    + "uuid VARCHAR(36) NOT NULL, "
                    + "slot VARCHAR(32) NOT NULL, "
                    + "cosmetic VARCHAR(64) NOT NULL, "
                    + "PRIMARY KEY (uuid, slot))");
        }
        plugin.getLogger().info("Speicher bereit (" + (mysql ? "MySQL - netzwerkweit" : "SQLite - lokal") + ").");
    }

    private synchronized Connection connection() throws SQLException {
        if (connection == null || !connection.isValid(2)) {
            if (connection != null) {
                try {
                    connection.close();
                } catch (SQLException ignored) {
                    // alte Verbindung ist ohnehin kaputt
                }
            }
            connection = mysql
                    ? DriverManager.getConnection(url, user, password)
                    : DriverManager.getConnection(url);
        }
        return connection;
    }

    /** Blockierend - nur asynchron aufrufen (PreLogin / Async-Task). */
    public void loadIntoCache(UUID uuid) {
        Map<String, String> data = new ConcurrentHashMap<>();
        synchronized (this) {
            try (PreparedStatement ps = connection().prepareStatement(
                    "SELECT slot, cosmetic FROM cosmetic_selection WHERE uuid = ?")) {
                ps.setString(1, uuid.toString());
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        data.put(rs.getString(1), rs.getString(2));
                    }
                }
            } catch (SQLException e) {
                plugin.getLogger().log(Level.WARNING, "Konnte Kosmetik von " + uuid + " nicht laden", e);
            }
        }
        cache.put(uuid, data);
    }

    public String cached(UUID uuid, String slot) {
        Map<String, String> data = cache.get(uuid);
        return data == null ? null : data.get(slot);
    }

    public void evict(UUID uuid) {
        cache.remove(uuid);
    }

    /** {@code cosmetic == null} entfernt die Auswahl. */
    public void saveAsync(UUID uuid, String slot, String cosmetic) {
        Map<String, String> data = cache.computeIfAbsent(uuid, k -> new ConcurrentHashMap<>());
        if (cosmetic == null) {
            data.remove(slot);
        } else {
            data.put(slot, cosmetic);
        }
        executor.execute(() -> save(uuid, slot, cosmetic));
    }

    private synchronized void save(UUID uuid, String slot, String cosmetic) {
        try {
            if (cosmetic == null) {
                try (PreparedStatement ps = connection().prepareStatement(
                        "DELETE FROM cosmetic_selection WHERE uuid = ? AND slot = ?")) {
                    ps.setString(1, uuid.toString());
                    ps.setString(2, slot);
                    ps.executeUpdate();
                }
                return;
            }
            String sql = mysql
                    ? "INSERT INTO cosmetic_selection (uuid, slot, cosmetic) VALUES (?, ?, ?) "
                    + "ON DUPLICATE KEY UPDATE cosmetic = VALUES(cosmetic)"
                    : "INSERT INTO cosmetic_selection (uuid, slot, cosmetic) VALUES (?, ?, ?) "
                    + "ON CONFLICT(uuid, slot) DO UPDATE SET cosmetic = excluded.cosmetic";
            try (PreparedStatement ps = connection().prepareStatement(sql)) {
                ps.setString(1, uuid.toString());
                ps.setString(2, slot);
                ps.setString(3, cosmetic);
                ps.executeUpdate();
            }
        } catch (SQLException e) {
            plugin.getLogger().log(Level.WARNING, "Konnte Kosmetik von " + uuid + " nicht speichern", e);
        }
    }

    public void close() {
        executor.shutdown();
        try {
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                plugin.getLogger().warning("Nicht alle Speichervorgaenge wurden rechtzeitig beendet.");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        synchronized (this) {
            if (connection != null) {
                try {
                    connection.close();
                } catch (SQLException ignored) {
                    // beim Herunterfahren egal
                }
            }
        }
    }
}
