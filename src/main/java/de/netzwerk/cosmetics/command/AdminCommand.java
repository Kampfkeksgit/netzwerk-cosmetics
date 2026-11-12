package de.netzwerk.cosmetics.command;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;

/** /cosmeticsadmin reload | pack [spieler] */
public final class AdminCommand implements CommandExecutor, TabCompleter {

    private final CosmeticsPlugin plugin;

    public AdminCommand(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (args.length == 0) {
            return false;
        }
        switch (args[0].toLowerCase(Locale.ROOT)) {
            case "reload" -> {
                plugin.reload();
                plugin.messages().send(sender, "reloaded");
            }
            case "pack" -> {
                Player target = args.length > 1 ? Bukkit.getPlayerExact(args[1])
                        : sender instanceof Player p ? p : null;
                if (target == null) {
                    sender.sendMessage("Spieler nicht gefunden.");
                    return true;
                }
                plugin.packService().send(target);
                plugin.messages().send(sender, "pack-sent", Placeholder.unparsed("player", target.getName()));
            }
            default -> {
                return false;
            }
        }
        return true;
    }

    @Override
    public List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                      @NotNull String label, @NotNull String[] args) {
        if (args.length == 1) {
            return List.of("reload", "pack");
        }
        if (args.length == 2 && args[0].equalsIgnoreCase("pack")) {
            List<String> names = new ArrayList<>();
            Bukkit.getOnlinePlayers().forEach(p -> names.add(p.getName()));
            return names;
        }
        return List.of();
    }
}
