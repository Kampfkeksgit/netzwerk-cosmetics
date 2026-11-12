package de.netzwerk.cosmetics;

import de.netzwerk.cosmetics.command.AdminCommand;
import de.netzwerk.cosmetics.command.WardrobeCommand;
import de.netzwerk.cosmetics.command.WingsCommand;
import de.netzwerk.cosmetics.gui.WardrobeMenu;
import de.netzwerk.cosmetics.listener.PlayerListener;
import de.netzwerk.cosmetics.pack.ResourcePackService;
import de.netzwerk.cosmetics.storage.CosmeticStorage;
import de.netzwerk.cosmetics.wings.WingManager;
import de.netzwerk.cosmetics.wings.WingRegistry;
import de.netzwerk.cosmetics.wings.WingSettings;
import java.util.Objects;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.PluginCommand;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

public final class CosmeticsPlugin extends JavaPlugin {

    private Messages messages;
    private CosmeticStorage storage;
    private WingRegistry wingRegistry;
    private WingManager wingManager;
    private ResourcePackService packService;

    @Override
    public void onEnable() {
        saveDefaultConfig();

        messages = new Messages(this);
        wingRegistry = new WingRegistry(this);
        wingRegistry.load(getConfig());

        storage = new CosmeticStorage(this);
        try {
            storage.init();
        } catch (Exception e) {
            getLogger().severe("Datenbank konnte nicht geoeffnet werden: " + e.getMessage());
            Bukkit.getPluginManager().disablePlugin(this);
            return;
        }

        wingManager = new WingManager(this, WingSettings.fromConfig(getConfig()));
        wingManager.start();

        packService = new ResourcePackService(this);
        packService.start();

        Bukkit.getPluginManager().registerEvents(new PlayerListener(this), this);
        Bukkit.getPluginManager().registerEvents(new WardrobeMenu.Listener(), this);

        register("garderobe", new WardrobeCommand(this));
        register("fluegel", new WingsCommand(this));
        register("cosmeticsadmin", new AdminCommand(this));

        // /reload oder Plugin-Neustart: bereits verbundene Spieler wieder ausstatten
        for (Player player : Bukkit.getOnlinePlayers()) {
            storage.restore(player);
        }
    }

    @Override
    public void onDisable() {
        if (wingManager != null) {
            wingManager.shutdown();
        }
        if (packService != null) {
            packService.stop();
        }
        if (storage != null) {
            storage.close();
        }
    }

    /** /cosmeticsadmin reload */
    public void reload() {
        reloadConfig();
        messages = new Messages(this);
        wingRegistry.load(getConfig());
        wingManager.updateSettings(WingSettings.fromConfig(getConfig()));
        packService.stop();
        packService.start();
        for (Player player : Bukkit.getOnlinePlayers()) {
            wingManager.restoreFromStorage(player);
        }
    }

    private <T extends CommandExecutor & TabCompleter> void register(String name, T handler) {
        PluginCommand command = Objects.requireNonNull(getCommand(name), "Befehl fehlt in plugin.yml: " + name);
        command.setExecutor(handler);
        command.setTabCompleter(handler);
    }

    public Messages messages() {
        return messages;
    }

    public CosmeticStorage storage() {
        return storage;
    }

    public WingRegistry wingRegistry() {
        return wingRegistry;
    }

    public WingManager wingManager() {
        return wingManager;
    }

    public ResourcePackService packService() {
        return packService;
    }
}
