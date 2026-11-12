package de.netzwerk.cosmetics.listener;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import de.netzwerk.cosmetics.Messages;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.AsyncPlayerPreLoginEvent;
import org.bukkit.event.player.PlayerChangedWorldEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerResourcePackStatusEvent;
import org.bukkit.event.player.PlayerTeleportEvent;

public final class PlayerListener implements Listener {

    private final CosmeticsPlugin plugin;

    public PlayerListener(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    /** Laeuft asynchron, bevor der Spieler den Server betritt -> DB-Zugriff blockiert nichts. */
    @EventHandler(priority = EventPriority.MONITOR)
    public void onPreLogin(AsyncPlayerPreLoginEvent event) {
        if (event.getLoginResult() == AsyncPlayerPreLoginEvent.Result.ALLOWED) {
            plugin.storage().loadIntoCache(event.getUniqueId());
        }
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        Player player = event.getPlayer();
        if (plugin.getConfig().getBoolean("resource-pack.send-on-join", true)) {
            // kurz warten, bis der Client vollstaendig in der Welt ist
            Bukkit.getScheduler().runTaskLater(plugin, () -> {
                if (player.isOnline()) {
                    plugin.packService().send(player);
                }
            }, 5L);
        }
        plugin.storage().restore(player);
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        plugin.wingManager().remove(event.getPlayer());
        plugin.armorManager().remove(event.getPlayer());
        plugin.storage().evict(event.getPlayer().getUniqueId());
    }

    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onTeleport(PlayerTeleportEvent event) {
        // Paper wirft Passagiere beim Teleport ab - Fluegel kurz weg und am Ziel neu aufsetzen
        plugin.wingManager().hideTemporarily(event.getPlayer(), 2);
    }

    @EventHandler
    public void onWorldChange(PlayerChangedWorldEvent event) {
        plugin.wingManager().hideTemporarily(event.getPlayer(), 2);
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onDeath(PlayerDeathEvent event) {
        plugin.wingManager().hideTemporarily(event.getPlayer(), 1);
    }

    @EventHandler
    public void onPackStatus(PlayerResourcePackStatusEvent event) {
        if (!plugin.packService().isEnabled()
                || !plugin.getConfig().getBoolean("resource-pack.kick-on-fail", true)
                || !plugin.getConfig().getBoolean("resource-pack.required", true)) {
            return;
        }
        switch (event.getStatus()) {
            case DECLINED, FAILED_DOWNLOAD, INVALID_URL, FAILED_RELOAD, DISCARDED -> {
                Player player = event.getPlayer();
                plugin.getLogger().info(player.getName() + ": Resource Pack " + event.getStatus());
                player.kick(Messages.parse(plugin.getConfig().getString("resource-pack.kick-message", "")));
            }
            default -> {
                // ACCEPTED, DOWNLOADED, SUCCESSFULLY_LOADED: alles gut
            }
        }
    }
}
