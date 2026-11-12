package de.netzwerk.cosmetics.gui;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import de.netzwerk.cosmetics.Messages;
import de.netzwerk.cosmetics.armor.ArmorSet;
import de.netzwerk.cosmetics.wings.WingType;
import java.util.ArrayList;
import java.util.List;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.TextColor;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Sound;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

/**
 * Garderobe mit eigenem Hintergrundbild (Font-Glyph im Titel) und eigenen Icons
 * (Item-Modelle aus dem Resource Pack). Layout passt zu textures/gui/wardrobe.png:
 *
 * <pre>
 *  Reihe 0-3: Spalten 1-7 = Fluegel bzw. Ruestungen (28 pro Seite)
 *  Reihe 5:   45 = zurueck, 48 = ablegen, 49 = schliessen, 50 = Reiter wechseln, 53 = weiter
 * </pre>
 */
public final class WardrobeMenu implements InventoryHolder {

    private enum Tab { WINGS, ARMOR }

    private static final int SLOT_PREV = 45;
    private static final int SLOT_REMOVE = 48;
    private static final int SLOT_CLOSE = 49;
    private static final int SLOT_TAB = 50;
    private static final int SLOT_NEXT = 53;
    private static final int[] CONTENT_SLOTS = buildContentSlots();

    private static final NamespacedKey ICON_PREV = new NamespacedKey("cosmetics", "gui/prev");
    private static final NamespacedKey ICON_NEXT = new NamespacedKey("cosmetics", "gui/next");
    private static final NamespacedKey ICON_REMOVE = new NamespacedKey("cosmetics", "gui/remove");
    private static final NamespacedKey ICON_CLOSE = new NamespacedKey("cosmetics", "gui/close");

    private final CosmeticsPlugin plugin;
    private final Player viewer;
    private final Inventory inventory;
    private final List<WingType> wingsOnPage = new ArrayList<>();
    private final List<ArmorSet> armorOnPage = new ArrayList<>();
    private Tab tab = Tab.WINGS;
    private int page;

    private WardrobeMenu(CosmeticsPlugin plugin, Player viewer) {
        this.plugin = plugin;
        this.viewer = viewer;
        Component title = Component.text(plugin.messages().raw("menu-title")).color(TextColor.color(0xE6DAFF));
        this.inventory = Bukkit.createInventory(this, 54, GuiFont.backgroundTitle(GuiFont.WARDROBE, title));
    }

    public static void open(CosmeticsPlugin plugin, Player player) {
        WardrobeMenu menu = new WardrobeMenu(plugin, player);
        menu.render();
        player.openInventory(menu.inventory);
    }

    @Override
    public Inventory getInventory() {
        return inventory;
    }

    private static int[] buildContentSlots() {
        int[] slots = new int[28];
        int i = 0;
        for (int row = 0; row < 4; row++) {
            for (int col = 1; col <= 7; col++) {
                slots[i++] = row * 9 + col;
            }
        }
        return slots;
    }

    private void render() {
        inventory.clear();
        wingsOnPage.clear();
        armorOnPage.clear();

        List<WingType> wings = new ArrayList<>(plugin.wingRegistry().all());
        List<ArmorSet> armor = new ArrayList<>(plugin.armorRegistry().all());
        int total = tab == Tab.WINGS ? wings.size() : armor.size();
        int pages = Math.max(1, (total + CONTENT_SLOTS.length - 1) / CONTENT_SLOTS.length);
        page = Math.max(0, Math.min(page, pages - 1));
        int start = page * CONTENT_SLOTS.length;

        if (tab == Tab.WINGS) {
            WingType current = plugin.wingManager().current(viewer);
            for (int i = 0; i < CONTENT_SLOTS.length && start + i < wings.size(); i++) {
                WingType wing = wings.get(start + i);
                wingsOnPage.add(wing);
                inventory.setItem(CONTENT_SLOTS[i], icon(wing.iconModel(), wing.name(), wing.lore(),
                        wing.equals(current), wing.canUse(viewer)));
            }
        } else {
            ArmorSet current = plugin.armorManager().current(viewer);
            for (int i = 0; i < CONTENT_SLOTS.length && start + i < armor.size(); i++) {
                ArmorSet set = armor.get(start + i);
                armorOnPage.add(set);
                inventory.setItem(CONTENT_SLOTS[i], icon(set.iconModel(), set.name(), set.lore(),
                        set.equals(current), set.canUse(viewer)));
            }
        }

        if (page > 0) {
            inventory.setItem(SLOT_PREV, button(ICON_PREV, "<#b48cff>« Vorherige Seite"));
        }
        if (page < pages - 1) {
            inventory.setItem(SLOT_NEXT, button(ICON_NEXT, "<#b48cff>Naechste Seite »"));
        }
        inventory.setItem(SLOT_REMOVE, button(ICON_REMOVE,
                tab == Tab.WINGS ? "<#ffbe50>Fluegel ablegen" : "<#ffbe50>Ruestung ablegen"));
        inventory.setItem(SLOT_CLOSE, button(ICON_CLOSE, "<#ff5a64>Schliessen"));

        // Reiter wechseln: zeigt als Icon das erste Element des jeweils anderen Reiters
        if (tab == Tab.WINGS && !armor.isEmpty()) {
            inventory.setItem(SLOT_TAB, button(armor.get(0).iconModel(), "<#7fd8ff>Zu den Ruestungen »"));
        } else if (tab == Tab.ARMOR && !wings.isEmpty()) {
            inventory.setItem(SLOT_TAB, button(wings.get(0).iconModel(), "<#7fd8ff>« Zu den Fluegeln"));
        }
    }

    private ItemStack icon(NamespacedKey model, Component name, List<Component> baseLore,
                           boolean equipped, boolean usable) {
        ItemStack item = new ItemStack(Material.PAPER);
        ItemMeta meta = item.getItemMeta();
        meta.setItemModel(model);
        meta.displayName(name);
        List<Component> lore = new ArrayList<>(baseLore);
        lore.add(Component.empty());
        if (equipped) {
            lore.add(plugin.messages().item("equipped-lore"));
            meta.setEnchantmentGlintOverride(true);
        } else if (usable) {
            lore.add(plugin.messages().item("click-lore"));
        } else {
            lore.add(plugin.messages().item("locked-lore"));
        }
        meta.lore(lore);
        item.setItemMeta(meta);
        return item;
    }

    private static ItemStack button(NamespacedKey model, String name) {
        ItemStack item = new ItemStack(Material.PAPER);
        ItemMeta meta = item.getItemMeta();
        meta.setItemModel(model);
        meta.displayName(Messages.noItalic(Messages.parse(name)));
        item.setItemMeta(meta);
        return item;
    }

    private void click(int slot) {
        switch (slot) {
            case SLOT_PREV -> {
                page--;
                render();
                playClick();
            }
            case SLOT_NEXT -> {
                page++;
                render();
                playClick();
            }
            case SLOT_TAB -> {
                if (inventory.getItem(SLOT_TAB) != null) {
                    tab = tab == Tab.WINGS ? Tab.ARMOR : Tab.WINGS;
                    page = 0;
                    render();
                    playClick();
                }
            }
            case SLOT_CLOSE -> viewer.closeInventory();
            case SLOT_REMOVE -> removeCurrent();
            default -> {
                for (int i = 0; i < CONTENT_SLOTS.length; i++) {
                    if (CONTENT_SLOTS[i] != slot) {
                        continue;
                    }
                    if (tab == Tab.WINGS && i < wingsOnPage.size()) {
                        selectWing(wingsOnPage.get(i));
                    } else if (tab == Tab.ARMOR && i < armorOnPage.size()) {
                        selectArmor(armorOnPage.get(i));
                    }
                    return;
                }
            }
        }
    }

    private void removeCurrent() {
        if (tab == Tab.WINGS) {
            if (plugin.wingManager().current(viewer) == null) {
                return;
            }
            plugin.wingManager().unequip(viewer, true);
            plugin.messages().send(viewer, "removed");
        } else {
            if (plugin.armorManager().current(viewer) == null) {
                return;
            }
            plugin.armorManager().unequip(viewer, true);
            plugin.messages().send(viewer, "armor-removed");
        }
        playClick();
        render();
    }

    private void selectWing(WingType wing) {
        if (!wing.canUse(viewer)) {
            deny("no-permission");
            return;
        }
        if (wing.equals(plugin.wingManager().current(viewer))) {
            return;
        }
        plugin.wingManager().equip(viewer, wing, true);
        plugin.messages().send(viewer, "equipped", Placeholder.component("name", wing.name()));
        viewer.playSound(viewer.getLocation(), Sound.ITEM_ARMOR_EQUIP_ELYTRA, 0.8f, 1.2f);
        render();
    }

    private void selectArmor(ArmorSet set) {
        if (!set.canUse(viewer)) {
            deny("armor-no-permission");
            return;
        }
        if (set.equals(plugin.armorManager().current(viewer))) {
            return;
        }
        plugin.armorManager().equip(viewer, set, true);
        plugin.messages().send(viewer, "equipped", Placeholder.component("name", set.name()));
        viewer.playSound(viewer.getLocation(), Sound.ITEM_ARMOR_EQUIP_IRON, 0.8f, 1.1f);
        render();
    }

    private void deny(String messageKey) {
        plugin.messages().send(viewer, messageKey);
        viewer.playSound(viewer.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.6f, 1f);
    }

    private void playClick() {
        viewer.playSound(viewer.getLocation(), Sound.UI_BUTTON_CLICK, 0.4f, 1.4f);
    }

    /** Event-Listener fuer alle offenen Garderoben. */
    public static final class Listener implements org.bukkit.event.Listener {

        @EventHandler(ignoreCancelled = true)
        public void onClick(InventoryClickEvent event) {
            if (!(event.getInventory().getHolder(false) instanceof WardrobeMenu menu)) {
                return;
            }
            event.setCancelled(true);
            if (event.getClickedInventory() == menu.inventory) {
                menu.click(event.getSlot());
            }
        }

        @EventHandler(ignoreCancelled = true)
        public void onDrag(InventoryDragEvent event) {
            if (event.getInventory().getHolder(false) instanceof WardrobeMenu) {
                event.setCancelled(true);
            }
        }
    }
}
