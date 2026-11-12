package de.netzwerk.cosmetics.wings;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.NamespacedKey;
import org.bukkit.World;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.Player;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.scheduler.BukkitTask;

/** Verwaltet alle aktiven Fluegel und tickt sie. */
public final class WingManager {

    public static final String SLOT = "wings";

    private final CosmeticsPlugin plugin;
    private final NamespacedKey markerKey;
    private final Map<UUID, WingInstance> active = new HashMap<>();
    private WingSettings settings;
    private BukkitTask task;

    public WingManager(CosmeticsPlugin plugin, WingSettings settings) {
        this.plugin = plugin;
        this.settings = settings;
        this.markerKey = new NamespacedKey(plugin, "wing_part");
    }

    public void start() {
        removeOrphans();
        task = Bukkit.getScheduler().runTaskTimer(plugin, this::tick, 1L, 1L);
    }

    public void shutdown() {
        if (task != null) {
            task.cancel();
        }
        active.values().forEach(WingInstance::despawn);
        active.clear();
        removeOrphans();
    }

    public void updateSettings(WingSettings settings) {
        this.settings = settings;
        active.values().forEach(WingInstance::despawn); // werden im naechsten Tick neu gebaut
    }

    private void tick() {
        Iterator<WingInstance> it = active.values().iterator();
        while (it.hasNext()) {
            WingInstance instance = it.next();
            if (!instance.player().isOnline()) {
                instance.despawn();
                it.remove();
                continue;
            }
            instance.tick(settings);
        }
    }

    // ------------------------------------------------------------------ API

    public WingType current(Player player) {
        WingInstance instance = active.get(player.getUniqueId());
        return instance == null ? null : instance.type();
    }

    public void equip(Player player, WingType type, boolean save) {
        WingInstance old = active.remove(player.getUniqueId());
        if (old != null) {
            old.despawn();
        }
        active.put(player.getUniqueId(), new WingInstance(plugin, markerKey, player, type));
        if (save) {
            plugin.storage().saveAsync(player.getUniqueId(), SLOT, type.id());
        }
    }

    public void unequip(Player player, boolean save) {
        WingInstance old = active.remove(player.getUniqueId());
        if (old != null) {
            old.despawn();
        }
        if (save) {
            plugin.storage().saveAsync(player.getUniqueId(), SLOT, null);
        }
    }

    /** Stellt die gespeicherte Auswahl wieder her (Join, Reload). */
    public void restoreFromStorage(Player player) {
        String id = plugin.storage().cached(player.getUniqueId(), SLOT);
        WingType type = plugin.wingRegistry().get(id);
        if (type != null && type.canUse(player)) {
            equip(player, type, false);
        } else {
            unequip(player, false);
        }
    }

    /** Beim Verlassen des Servers. */
    public void remove(Player player) {
        WingInstance old = active.remove(player.getUniqueId());
        if (old != null) {
            old.despawn();
        }
    }

    /** Teleport / Weltwechsel / Tod: kurz ausblenden, dann sauber neu aufsetzen. */
    public void hideTemporarily(Player player, int ticks) {
        WingInstance instance = active.get(player.getUniqueId());
        if (instance != null) {
            instance.hideFor(ticks);
        }
    }

    public boolean isWingPart(org.bukkit.entity.Entity entity) {
        return entity.getPersistentDataContainer().has(markerKey, PersistentDataType.BYTE);
    }

    /** Entfernt Fluegel-Entities, die z.B. nach einem Absturz uebrig geblieben sind. */
    private void removeOrphans() {
        for (World world : Bukkit.getWorlds()) {
            for (ItemDisplay display : world.getEntitiesByClass(ItemDisplay.class)) {
                if (isWingPart(display)) {
                    display.remove();
                }
            }
        }
    }
}
