package de.netzwerk.cosmetics.armor;

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

/** Alle in der config.yml definierten Ruestungssets (armor.sets), in Konfigurations-Reihenfolge. */
public final class ArmorRegistry {

    private final CosmeticsPlugin plugin;
    private final Map<String, ArmorSet> sets = new LinkedHashMap<>();

    public ArmorRegistry(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    public void load(FileConfiguration config) {
        sets.clear();
        ConfigurationSection section = config.getConfigurationSection("armor.sets");
        if (section == null) {
            plugin.getLogger().info("Keine Ruestungssets in der config.yml (Abschnitt 'armor.sets').");
            return;
        }
        for (String id : section.getKeys(false)) {
            ConfigurationSection s = section.getConfigurationSection(id);
            if (s == null) {
                continue;
            }
            String key = id.toLowerCase(Locale.ROOT);
            NamespacedKey asset = NamespacedKey.fromString(s.getString("asset", "cosmetics:" + key));
            NamespacedKey icon = NamespacedKey.fromString(s.getString("icon", "cosmetics:armor/" + key + "_icon"));
            if (asset == null || icon == null) {
                plugin.getLogger().warning("Ungueltiges Asset/Icon fuer Ruestung '" + id + "'.");
                continue;
            }
            List<Component> lore = new ArrayList<>();
            for (String line : s.getStringList("lore")) {
                lore.add(Messages.noItalic(Messages.parse(line)));
            }
            Component name = Messages.noItalic(Messages.parse(s.getString("name", id)));
            sets.put(key, new ArmorSet(key, name, List.copyOf(lore),
                    s.getString("permission", "cosmetics.armor." + key), asset, icon));
        }
        plugin.getLogger().info(sets.size() + " Ruestungssets geladen.");
    }

    public ArmorSet get(String id) {
        return id == null ? null : sets.get(id.toLowerCase(Locale.ROOT));
    }

    public Collection<ArmorSet> all() {
        return Collections.unmodifiableCollection(sets.values());
    }
}
