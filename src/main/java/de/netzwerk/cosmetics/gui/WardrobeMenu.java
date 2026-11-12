package de.netzwerk.cosmetics.gui;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import de.netzwerk.cosmetics.Messages;
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
 *  Reihe 0-3: Spalten 1-7 = Fluegel (28 pro Seite)
 *  Reihe 5:   45 = zurueck, 48 = ablegen, 49 = schliessen, 53 = weiter
 * </pre>
 */
public final class WardrobeMenu implements InventoryHolder {

    private static final int SLOT_PREV = 45;
    private static final int SLOT_REMOVE = 48;
    private static final int SLOT_CLOSE = 49;
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

        List<WingType> all = new ArrayList<>(plugin.wingRegistry().all());
        int pages = Math.max(1, (all.size() + CONTENT_SLOTS.length - 1) / CONTENT_SLOTS.length);
        page = Math.max(0, Math.min(page, pages - 1));
        WingType current = plugin.wingManager().current(viewer);

        int start = page * CONTENT_SLOTS.length;
        for (int i = 0; i < CONTENT_SLOTS.length && start + i < all.size(); i++) {
            WingType wing = all.get(start + i);
            wingsOnPage.add(wing);
            inventory.setItem(CONTENT_SLOTS[i], wingIcon(wing, wing.equals(current)));
        }

        if (page > 0) {
            inventory.setItem(SLOT_PREV, button(ICON_PREV, "<#b48cff>« Vorherige Seite"));
        }
        if (page < pages - 1) {
            inventory.setItem(SLOT_NEXT, button(ICON_NEXT, "<#b48cff>Naechste Seite »"));
        }
        inventory.setItem(SLOT_REMOVE, button(ICON_REMOVE, "<#ffbe50>Fluegel ablegen"));
        inventory.setItem(SLOT_CLOSE, button(ICON_CLOSE, "<#ff5a64>Schliessen"));
    }

    private ItemStack wingIcon(WingType wing, boolean equipped) {
        ItemStack item = new ItemStack(Material.PAPER);
        ItemMeta meta = item.getItemMeta();
        meta.setItemModel(wing.iconModel());
        meta.displayName(wing.name());
        List<Component> lore = new ArrayList<>(wing.lore());
        lore.add(Component.empty());
        if (equipped) {
            lore.add(plugin.messages().item("equipped-lore"));
            meta.setEnchantmentGlintOverride(true);
        } else if (wing.canUse(viewer)) {
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
            case SLOT_CLOSE -> viewer.closeInventory();
            case SLOT_REMOVE -> {
                if (plugin.wingManager().current(viewer) != null) {
                    plugin.wingManager().unequip(viewer, true);
                    plugin.messages().send(viewer, "removed");
                    playClick();
                    render();
                }
            }
            default -> {
                for (int i = 0; i < CONTENT_SLOTS.length && i < wingsOnPage.size(); i++) {
                    if (CONTENT_SLOTS[i] == slot) {
                        selectWing(wingsOnPage.get(i));
                        return;
                    }
                }
            }
        }
    }

    private void selectWing(WingType wing) {
        if (!wing.canUse(viewer)) {
            plugin.messages().send(viewer, "no-permission");
            viewer.playSound(viewer.getLocation(), Sound.ENTITY_VILLAGER_NO, 0.6f, 1f);
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
