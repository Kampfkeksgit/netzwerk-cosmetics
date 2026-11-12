package de.netzwerk.cosmetics.pack;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import de.netzwerk.cosmetics.CosmeticsPlugin;
import de.netzwerk.cosmetics.Messages;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import net.kyori.adventure.resource.ResourcePackInfo;
import net.kyori.adventure.resource.ResourcePackRequest;
import net.kyori.adventure.text.Component;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;

/**
 * Stellt das Resource Pack bereit und schickt es an Spieler.
 *
 * <p>Modus {@code internal}: Ein winziger HTTP-Server im Plugin liefert die ZIP aus.
 * Modus {@code external}: Die ZIP liegt auf einem beliebigen Webserver.
 *
 * <p>Die Pack-ID ist fest und der SHA-1 wird mitgeschickt. Bekommt ein Client beim
 * Serverwechsel im Netzwerk dasselbe Pack (gleiche ID, URL und Hash) erneut, laedt er es
 * nicht noch einmal herunter.
 */
public final class ResourcePackService {

    public static final UUID PACK_ID = UUID.nameUUIDFromBytes("netzwerk-cosmetics-pack".getBytes(StandardCharsets.UTF_8));
    private static final String PACK_FILE = "resourcepack.zip";

    private final CosmeticsPlugin plugin;
    private HttpServer server;
    private ExecutorService httpExecutor;
    private byte[] packBytes;
    private String sha1;
    private URI url;
    private boolean enabled;

    public ResourcePackService(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    public void start() {
        enabled = false;
        ConfigurationSection c = plugin.getConfig().getConfigurationSection("resource-pack");
        if (c == null) {
            plugin.getLogger().warning("Abschnitt 'resource-pack' fehlt - Pack wird nicht gesendet.");
            return;
        }
        try {
            File file = preparePackFile(c.getBoolean("overwrite-on-start", true));
            String mode = c.getString("mode", "internal");
            if ("external".equalsIgnoreCase(mode)) {
                url = URI.create(c.getString("external.url", ""));
                String configured = c.getString("external.sha1", "");
                sha1 = configured.isBlank() ? sha1Hex(Files.readAllBytes(file.toPath())) : configured.toLowerCase();
            } else {
                packBytes = Files.readAllBytes(file.toPath());
                sha1 = sha1Hex(packBytes);
                startHttpServer(c.getString("internal.bind", "0.0.0.0"), c.getInt("internal.port", 8085));
                String publicUrl = c.getString("internal.public-url", "");
                if (publicUrl.contains("DEINE-SERVER-IP")) {
                    plugin.getLogger().warning("resource-pack.internal.public-url ist noch nicht eingestellt!");
                }
                // ?h=<hash> verhindert, dass Clients/CDNs eine alte Version cachen
                url = URI.create(publicUrl + (publicUrl.contains("?") ? "&" : "?") + "h=" + sha1);
            }
            enabled = true;
            plugin.getLogger().info("Resource Pack bereit: " + url + " (SHA-1 " + sha1 + ")");
        } catch (Exception e) {
            plugin.getLogger().log(Level.SEVERE, "Resource Pack konnte nicht vorbereitet werden", e);
        }
    }

    public void stop() {
        if (server != null) {
            server.stop(0);
            server = null;
        }
        if (httpExecutor != null) {
            httpExecutor.shutdownNow();
            httpExecutor = null;
        }
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void send(Player player) {
        if (!enabled) {
            return;
        }
        ConfigurationSection c = plugin.getConfig().getConfigurationSection("resource-pack");
        boolean required = c == null || c.getBoolean("required", true);
        Component prompt = Messages.parse(c == null ? "" : c.getString("prompt", ""));
        ResourcePackInfo info = ResourcePackInfo.resourcePackInfo(PACK_ID, url, sha1);
        player.sendResourcePacks(ResourcePackRequest.resourcePackRequest()
                .packs(info)
                .required(required)
                .prompt(prompt)
                .replace(false)
                .build());
    }

    // ------------------------------------------------------------------

    private File preparePackFile(boolean overwrite) throws IOException {
        File file = new File(plugin.getDataFolder(), PACK_FILE);
        if (overwrite || !file.exists()) {
            try (InputStream in = plugin.getResource(PACK_FILE)) {
                if (in == null) {
                    if (file.exists()) {
                        return file;
                    }
                    throw new IOException(PACK_FILE + " ist weder in der JAR noch im Plugin-Ordner");
                }
                Files.createDirectories(file.getParentFile().toPath());
                Files.copy(in, file.toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
        }
        return file;
    }

    private void startHttpServer(String bind, int port) throws IOException {
        stop();
        server = HttpServer.create(new InetSocketAddress(bind, port), 0);
        httpExecutor = Executors.newFixedThreadPool(2, r -> {
            Thread t = new Thread(r, "NetzwerkCosmetics-HTTP");
            t.setDaemon(true);
            return t;
        });
        server.setExecutor(httpExecutor);
        server.createContext("/", this::handle);
        server.start();
        plugin.getLogger().info("Resource-Pack-Webserver laeuft auf " + bind + ":" + port);
    }

    private void handle(HttpExchange exchange) throws IOException {
        try (exchange) {
            String path = exchange.getRequestURI().getPath();
            if (!"GET".equals(exchange.getRequestMethod()) || !path.endsWith(".zip")) {
                exchange.sendResponseHeaders(404, -1);
                return;
            }
            byte[] data = packBytes;
            exchange.getResponseHeaders().set("Content-Type", "application/zip");
            exchange.getResponseHeaders().set("Cache-Control", "public, max-age=31536000, immutable");
            exchange.sendResponseHeaders(200, data.length);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write(data);
            }
        }
    }

    private static String sha1Hex(byte[] data) throws NoSuchAlgorithmException {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-1").digest(data));
    }
}
