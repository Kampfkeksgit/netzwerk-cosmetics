package de.netzwerk.cosmetics.wings;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import de.netzwerk.cosmetics.Messages;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import net.kyori.adventure.text.Component;
import org.bukkit.NamespacedKey;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;

/** Alle in der config.yml definierten Fluegel, in Konfigurations-Reihenfolge. */
public final class WingRegistry {

    private final CosmeticsPlugin plugin;
    private final Map<String, WingType> wings = new LinkedHashMap<>();

    public WingRegistry(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    public void load(FileConfiguration config) {
        wings.clear();
        ConfigurationSection section = config.getConfigurationSection("wings");
        if (section == null) {
            plugin.getLogger().warning("Keine Fluegel in der config.yml (Abschnitt 'wings') definiert.");
            return;
        }
        for (String id : section.getKeys(false)) {
            ConfigurationSection s = section.getConfigurationSection(id);
            if (s == null) {
                continue;
            }
            String model = s.getString("model", "cosmetics:wings/" + id);
            NamespacedKey left = NamespacedKey.fromString(model + "_left");
            NamespacedKey right = NamespacedKey.fromString(model + "_right");
            NamespacedKey icon = NamespacedKey.fromString(model + "_icon");
            if (left == null || right == null || icon == null) {
                plugin.getLogger().warning("Ungueltiges Modell fuer Fluegel '" + id + "': " + model);
                continue;
            }
            List<Component> lore = new ArrayList<>();
            for (String line : s.getStringList("lore")) {
                lore.add(Messages.noItalic(Messages.parse(line)));
            }
            Component name = Messages.noItalic(Messages.parse(s.getString("name", id)));
            String key = id.toLowerCase(Locale.ROOT);
            wings.put(key, new WingType(key, name, List.copyOf(lore),
                    s.getString("permission", "cosmetics.wings." + key), left, right, icon,
                    (float) s.getDouble("scale", 0), (float) s.getDouble("flap", 1.0)));
        }
        plugin.getLogger().info(wings.size() + " Fluegel geladen.");
    }

    public WingType get(String id) {
        return id == null ? null : wings.get(id.toLowerCase(Locale.ROOT));
    }

    public Collection<WingType> all() {
        return Collections.unmodifiableCollection(wings.values());
    }
}
