package de.netzwerk.cosmetics.armor;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Material;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.inventory.meta.components.EquippableComponent;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.scheduler.BukkitTask;

/**
 * Kosmetik-Ruestung, die NUR optisch angezeigt wird.
 *
 * <p>Die echten Ruestungsslots des Spielers bleiben unberuehrt (Schutz, Haltbarkeit, Inventar).
 * Anderen Spielern wird per Ausruestungs-Paket ein Item mit {@code equippable}-Komponente
 * vorgetaeuscht, dessen Aussehen aus dem Resource Pack kommt. Weil der Server bei jeder
 * echten Aenderung wieder die echte Ruestung sendet, wird die Anzeige regelmaessig aufgefrischt
 * ({@code armor.refresh-ticks}).
 *
 * <p>Der Traeger selbst sieht die Kosmetik-Ruestung nur mit {@code armor.show-self: true};
 * dann erscheinen die Kosmetik-Teile bei ihm aber auch als Geister-Items in den Ruestungsslots.
 */
public final class ArmorManager {

    public static final String SLOT = "armor";
    private static final EquipmentSlot[] SLOTS = {
            EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};

    private final CosmeticsPlugin plugin;
    private final Map<UUID, ArmorSet> active = new HashMap<>();
    private final Set<UUID> shown = new HashSet<>();
    private final Map<String, Map<EquipmentSlot, ItemStack>> itemCache = new HashMap<>();

    private int refreshTicks;
    private boolean showSelf;
    private double viewDistanceSquared;
    private BukkitTask task;

    public ArmorManager(CosmeticsPlugin plugin) {
        this.plugin = plugin;
        readSettings(plugin.getConfig());
    }

    private void readSettings(FileConfiguration config) {
        refreshTicks = Math.max(2, config.getInt("armor.refresh-ticks", 20));
        showSelf = config.getBoolean("armor.show-self", false);
        double distance = Math.max(8, config.getDouble("armor.view-distance", 64));
        viewDistanceSquared = distance * distance;
    }

    public void start() {
        task = Bukkit.getScheduler().runTaskTimer(plugin, this::tick, refreshTicks, refreshTicks);
    }

    public void shutdown() {
        if (task != null) {
            task.cancel();
            task = null;
        }
        for (UUID uuid : new HashSet<>(shown)) {
            Player player = Bukkit.getPlayer(uuid);
            if (player != null) {
                sendReal(player);
            }
        }
        shown.clear();
        active.clear();
    }

    /** Nach /cosmeticsadmin reload: Einstellungen und Sets neu einlesen. */
    public void reload() {
        shutdown();
        itemCache.clear();
        readSettings(plugin.getConfig());
        start();
    }

    private void tick() {
        Iterator<Map.Entry<UUID, ArmorSet>> it = active.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<UUID, ArmorSet> entry = it.next();
            Player player = Bukkit.getPlayer(entry.getKey());
            if (player == null || !player.isOnline()) {
                shown.remove(entry.getKey());
                it.remove();
                continue;
            }
            refresh(player, entry.getValue());
        }
    }

    private void refresh(Player player, ArmorSet set) {
        if (shouldShow(player)) {
            send(player, items(set));
            shown.add(player.getUniqueId());
        } else if (shown.remove(player.getUniqueId())) {
            sendReal(player);
        }
    }

    private static boolean shouldShow(Player player) {
        return !player.isDead()
                && player.getGameMode() != GameMode.SPECTATOR
                && !player.hasPotionEffect(PotionEffectType.INVISIBILITY);
    }

    // ------------------------------------------------------------------ API

    public ArmorSet current(Player player) {
        return active.get(player.getUniqueId());
    }

    public void equip(Player player, ArmorSet set, boolean save) {
        active.put(player.getUniqueId(), set);
        refresh(player, set);
        if (save) {
            plugin.storage().saveAsync(player.getUniqueId(), SLOT, set.id());
        }
    }

    public void unequip(Player player, boolean save) {
        active.remove(player.getUniqueId());
        if (shown.remove(player.getUniqueId())) {
            sendReal(player);
        }
        if (save) {
            plugin.storage().saveAsync(player.getUniqueId(), SLOT, null);
        }
    }

    /** Stellt die gespeicherte Auswahl wieder her (Join, Reload). */
    public void restoreFromStorage(Player player) {
        ArmorSet set = plugin.armorRegistry().get(plugin.storage().cached(player.getUniqueId(), SLOT));
        if (set != null && set.canUse(player)) {
            equip(player, set, false);
        } else {
            unequip(player, false);
        }
    }

    /** Beim Verlassen des Servers. */
    public void remove(Player player) {
        active.remove(player.getUniqueId());
        shown.remove(player.getUniqueId());
    }

    // ------------------------------------------------------------------ Anzeige

    private Map<EquipmentSlot, ItemStack> items(ArmorSet set) {
        return itemCache.computeIfAbsent(set.id(), id -> {
            Map<EquipmentSlot, ItemStack> items = new EnumMap<>(EquipmentSlot.class);
            for (EquipmentSlot slot : SLOTS) {
                ItemStack item = new ItemStack(Material.PAPER);
                ItemMeta meta = item.getItemMeta();
                EquippableComponent equippable = meta.getEquippable();
                equippable.setSlot(slot);
                equippable.setModel(set.asset());
                meta.setEquippable(equippable);
                meta.displayName(set.name());
                item.setItemMeta(meta);
                items.put(slot, item);
            }
            return items;
        });
    }

    private void sendReal(Player player) {
        Map<EquipmentSlot, ItemStack> real = new EnumMap<>(EquipmentSlot.class);
        for (EquipmentSlot slot : SLOTS) {
            ItemStack item = player.getInventory().getItem(slot);
            real.put(slot, item == null ? new ItemStack(Material.AIR) : item);
        }
        send(player, real);
        if (showSelf) {
            player.updateInventory();
        }
    }

    private void send(Player target, Map<EquipmentSlot, ItemStack> items) {
        for (Player viewer : target.getWorld().getPlayers()) {
            if (viewer.equals(target)) {
                if (showSelf) {
                    viewer.sendEquipmentChange(target, items);
                }
                continue;
            }
            if (viewer.canSee(target)
                    && viewer.getLocation().distanceSquared(target.getLocation()) <= viewDistanceSquared) {
                viewer.sendEquipmentChange(target, items);
            }
        }
    }
}
