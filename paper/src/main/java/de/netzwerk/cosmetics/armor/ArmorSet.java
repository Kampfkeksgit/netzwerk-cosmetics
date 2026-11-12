package de.netzwerk.cosmetics.armor;

import java.util.List;
import net.kyori.adventure.text.Component;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Player;

/**
 * Ein Kosmetik-Ruestungsset aus der config.yml (armor.sets).
 *
 * @param asset     Ruestungs-Aussehen aus dem Resource Pack (assets/&lt;ns&gt;/equipment/&lt;name&gt;.json)
 * @param iconModel Item-Modell fuer das Menue-Icon
 */
public record ArmorSet(
        String id,
        Component name,
        List<Component> lore,
        String permission,
        NamespacedKey asset,
        NamespacedKey iconModel
) {

    public boolean canUse(Player player) {
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }
}
