package de.netzwerk.cosmetics.wings;

import java.util.List;
import net.kyori.adventure.text.Component;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Player;

/**
 * Ein Fluegel-Typ aus der config.yml.
 *
 * @param leftModel  Item-Modell (assets/&lt;ns&gt;/items/...) fuer den linken Fluegel
 * @param rightModel Item-Modell fuer den rechten Fluegel
 * @param iconModel  Item-Modell fuer das Menue-Icon
 */
public record WingType(
        String id,
        Component name,
        List<Component> lore,
        String permission,
        NamespacedKey leftModel,
        NamespacedKey rightModel,
        NamespacedKey iconModel
) {

    public boolean canUse(Player player) {
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }
}
