package de.netzwerk.cosmetics.command;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import de.netzwerk.cosmetics.wings.WingType;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;

/** /fluegel &lt;id|aus&gt; */
public final class WingsCommand implements CommandExecutor, TabCompleter {

    private final CosmeticsPlugin plugin;

    public WingsCommand(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("Nur fuer Spieler.");
            return true;
        }
        if (args.length == 0) {
            return false; // zeigt usage aus plugin.yml
        }
        String id = args[0].toLowerCase(Locale.ROOT);
        if (id.equals("aus") || id.equals("off")) {
            plugin.wingManager().unequip(player, true);
            plugin.messages().send(player, "removed");
            return true;
        }
        WingType type = plugin.wingRegistry().get(id);
        if (type == null) {
            plugin.messages().send(player, "unknown-wing", Placeholder.unparsed("id", id));
            return true;
        }
        if (!type.canUse(player)) {
            plugin.messages().send(player, "no-permission");
            return true;
        }
        plugin.wingManager().equip(player, type, true);
        plugin.messages().send(player, "equipped", Placeholder.component("name", type.name()));
        return true;
    }

    @Override
    public List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                      @NotNull String label, @NotNull String[] args) {
        if (args.length != 1 || !(sender instanceof Player player)) {
            return List.of();
        }
        String prefix = args[0].toLowerCase(Locale.ROOT);
        List<String> result = new ArrayList<>();
        if ("aus".startsWith(prefix)) {
            result.add("aus");
        }
        for (WingType type : plugin.wingRegistry().all()) {
            if (type.id().startsWith(prefix) && type.canUse(player)) {
                result.add(type.id());
            }
        }
        return result;
    }
}
