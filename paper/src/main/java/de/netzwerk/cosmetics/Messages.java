package de.netzwerk.cosmetics;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.TextDecoration;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.ConfigurationSection;

/** Liest Texte aus config.yml (messages.*) und rendert sie mit MiniMessage. */
public final class Messages {

    private static final MiniMessage MM = MiniMessage.miniMessage();

    private final ConfigurationSection section;
    private final Component prefix;

    Messages(CosmeticsPlugin plugin) {
        ConfigurationSection s = plugin.getConfig().getConfigurationSection("messages");
        this.section = s != null ? s : plugin.getConfig().createSection("messages");
        this.prefix = MM.deserialize(section.getString("prefix", ""));
    }

    public String raw(String key) {
        return section.getString(key, key);
    }

    public Component get(String key, TagResolver... resolvers) {
        return MM.deserialize(raw(key), resolvers);
    }

    /** Fuer Item-Namen/Lore: ohne das kursive Standard-Styling von Minecraft. */
    public Component item(String key, TagResolver... resolvers) {
        return noItalic(get(key, resolvers));
    }

    public void send(CommandSender sender, String key, TagResolver... resolvers) {
        sender.sendMessage(prefix.append(get(key, resolvers)));
    }

    public static Component parse(String miniMessage, TagResolver... resolvers) {
        return MM.deserialize(miniMessage, resolvers);
    }

    public static Component noItalic(Component component) {
        return component.decorationIfAbsent(TextDecoration.ITALIC, TextDecoration.State.FALSE);
    }
}
