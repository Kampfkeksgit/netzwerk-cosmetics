package de.netzwerk.cosmetics;

import de.netzwerk.cosmetics.armor.ArmorManager;
import de.netzwerk.cosmetics.armor.ArmorRegistry;
import de.netzwerk.cosmetics.command.AdminCommand;
import de.netzwerk.cosmetics.command.ArmorCommand;
import de.netzwerk.cosmetics.command.WardrobeCommand;
import de.netzwerk.cosmetics.command.WingsCommand;
import de.netzwerk.cosmetics.gui.WardrobeMenu;
import de.netzwerk.cosmetics.listener.PlayerListener;
import de.netzwerk.cosmetics.pack.ResourcePackService;
import de.netzwerk.cosmetics.storage.CosmeticStorage;
import de.netzwerk.cosmetics.wings.WingManager;
import de.netzwerk.cosmetics.wings.WingRegistry;
import de.netzwerk.cosmetics.wings.WingSettings;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Objects;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.PluginCommand;
import org.bukkit.command.TabCompleter;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

public final class CosmeticsPlugin extends JavaPlugin {

    /** Abschnitte, in denen neue Eintraege aus der mitgelieferten config.yml nachgetragen werden. */
    private static final List<String> MERGED_SECTIONS = List.of("wings", "armor.sets", "messages");
    private static final List<String> MERGED_VALUES = List.of(
            "auto-add-new-entries", "armor.refresh-ticks", "armor.show-self", "armor.view-distance");

    private Messages messages;
    private CosmeticStorage storage;
    private WingRegistry wingRegistry;
    private WingManager wingManager;
    private ArmorRegistry armorRegistry;
    private ArmorManager armorManager;
    private ResourcePackService packService;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        mergeNewDefaults();

        messages = new Messages(this);
        wingRegistry = new WingRegistry(this);
        wingRegistry.load(getConfig());
        armorRegistry = new ArmorRegistry(this);
        armorRegistry.load(getConfig());

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
        armorManager = new ArmorManager(this);
        armorManager.start();

        packService = new ResourcePackService(this);
        packService.start();

        Bukkit.getPluginManager().registerEvents(new PlayerListener(this), this);
        Bukkit.getPluginManager().registerEvents(new WardrobeMenu.Listener(), this);

        register("garderobe", new WardrobeCommand(this));
        register("fluegel", new WingsCommand(this));
        register("ruestung", new ArmorCommand(this));
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
        if (armorManager != null) {
            armorManager.shutdown();
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
        mergeNewDefaults();
        messages = new Messages(this);
        wingRegistry.load(getConfig());
        armorRegistry.load(getConfig());
        wingManager.updateSettings(WingSettings.fromConfig(getConfig()));
        armorManager.reload();
        packService.stop();
        packService.start();
        for (Player player : Bukkit.getOnlinePlayers()) {
            restoreCosmetics(player);
        }
    }

    /** Legt dem Spieler alles an, was im Speicher fuer ihn hinterlegt ist. */
    public void restoreCosmetics(Player player) {
        wingManager.restoreFromStorage(player);
        armorManager.restoreFromStorage(player);
    }

    /**
     * Die config.yml auf dem Server wird nur beim allerersten Start angelegt. Damit neue Fluegel,
     * Ruestungen und Texte aus einem Plugin-Update trotzdem ankommen, werden FEHLENDE Eintraege
     * aus der mitgelieferten config.yml nachgetragen. Vorhandene Eintraege bleiben unveraendert.
     * Abschalten mit {@code auto-add-new-entries: false}.
     */
    private void mergeNewDefaults() {
        FileConfiguration config = getConfig();
        if (!config.getBoolean("auto-add-new-entries", true)) {
            return;
        }
        InputStream in = getResource("config.yml");
        if (in == null) {
            return;
        }
        YamlConfiguration defaults = YamlConfiguration.loadConfiguration(new InputStreamReader(in, StandardCharsets.UTF_8));
        int added = 0;
        for (String path : MERGED_SECTIONS) {
            ConfigurationSection section = defaults.getConfigurationSection(path);
            if (section == null) {
                continue;
            }
            for (String key : section.getKeys(false)) {
                String entry = path + "." + key;
                if (config.isSet(entry)) {
                    continue;
                }
                if (section.isConfigurationSection(key)) {
                    ConfigurationSection sub = section.getConfigurationSection(key);
                    for (String leaf : sub.getKeys(true)) {
                        if (!sub.isConfigurationSection(leaf)) {
                            config.set(entry + "." + leaf, sub.get(leaf));
                        }
                    }
                } else {
                    config.set(entry, section.get(key));
                }
                added++;
            }
        }
        for (String path : MERGED_VALUES) {
            if (!config.isSet(path) && defaults.isSet(path)) {
                config.set(path, defaults.get(path));
                added++;
            }
        }
        if (added > 0) {
            saveConfig();
            getLogger().info(added + " neue Eintraege aus dem Update in die config.yml uebernommen.");
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

    public ArmorRegistry armorRegistry() {
        return armorRegistry;
    }

    public ArmorManager armorManager() {
        return armorManager;
    }

    public ResourcePackService packService() {
        return packService;
    }
}
