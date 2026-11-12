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
 * @param scale      eigene Groesse (0 = Standard aus wing-settings.scale)
 * @param flapFactor Staerke des Fluegelschlags (1 = normal, 0.4 = steif wie Metall)
 */
public record WingType(
        String id,
        Component name,
        List<Component> lore,
        String permission,
        NamespacedKey leftModel,
        NamespacedKey rightModel,
        NamespacedKey iconModel,
        float scale,
        float flapFactor
) {

    public boolean canUse(Player player) {
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }
}
