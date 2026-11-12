package de.netzwerk.cosmetics.command;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import de.netzwerk.cosmetics.gui.WardrobeMenu;
import java.util.List;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;

/** /garderobe */
public final class WardrobeCommand implements CommandExecutor, TabCompleter {

    private final CosmeticsPlugin plugin;

    public WardrobeCommand(CosmeticsPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("Nur fuer Spieler.");
            return true;
        }
        WardrobeMenu.open(plugin, player);
        return true;
    }

    @Override
    public List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                      @NotNull String label, @NotNull String[] args) {
        return List.of();
    }
}
