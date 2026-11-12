import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;

/**
 * Prueft das Resource Pack mit den echten Parsern aus dem Minecraft-Client.
 *
 * Aufruf (siehe tools/validate-pack.sh):
 *   java -cp client.jar:<libs> tools/validator/PackValidator.java resourcepack
 */
public final class PackValidator {

    public static void main(String[] args) throws Exception {
        Path root = Path.of(args.length > 0 ? args[0] : "resourcepack");
        net.minecraft.SharedConstants.tryDetectVersion();
        net.minecraft.server.Bootstrap.bootStrap();
        // Nur die Registries, die zum Einlesen noetig sind (ClientBootstrap wuerde Grafik-Natives laden)
        net.minecraft.client.renderer.item.ItemModels.bootstrap();
        net.minecraft.client.renderer.item.properties.conditional.ConditionalItemModelProperties.bootstrap();
        net.minecraft.client.renderer.item.properties.select.SelectItemModelProperties.bootstrap();
        net.minecraft.client.renderer.item.properties.numeric.RangeSelectItemModelProperties.bootstrap();

        int ok = 0;
        int errors = 0;
        Path assets = root.resolve("assets");
        List<Path> files;
        try (Stream<Path> s = Files.walk(assets)) {
            files = s.filter(p -> p.toString().endsWith(".json")).sorted().toList();
        }
        for (Path file : files) {
            String rel = assets.relativize(file).toString().replace('\\', '/');
            try {
                if (rel.matches("[^/]+/models/.*")) {
                    try (Reader r = Files.newBufferedReader(file)) {
                        net.minecraft.client.resources.model.cuboid.CuboidModel.fromStream(r);
                    }
                } else if (rel.matches("[^/]+/items/.*")) {
                    JsonElement json = JsonParser.parseString(Files.readString(file));
                    net.minecraft.client.renderer.item.ClientItem.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow();
                } else if (rel.matches("[^/]+/font/.*")) {
                    JsonElement json = JsonParser.parseString(Files.readString(file));
                    for (JsonElement provider : json.getAsJsonObject().getAsJsonArray("providers")) {
                        net.minecraft.client.gui.font.providers.GlyphProviderDefinition.MAP_CODEC.codec()
                                .parse(JsonOps.INSTANCE, provider).getOrThrow();
                    }
                } else {
                    System.out.println("  (nicht geprueft) " + rel);
                    continue;
                }
                ok++;
            } catch (Throwable t) {
                errors++;
                System.out.println("FEHLER " + rel + ": " + t);
            }
        }
        System.out.println(ok + " Dateien OK, " + errors + " Fehler");
        System.exit(errors == 0 ? 0 : 1);
    }
}
