package de.netzwerk.cosmetics.wings;

import de.netzwerk.cosmetics.CosmeticsPlugin;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.entity.Player;
import org.bukkit.entity.Pose;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.util.Transformation;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * Die Fluegel eines einzelnen Spielers.
 *
 * <p>Jeder Fluegel ist ein {@link ItemDisplay}, das als Passagier auf dem Spieler sitzt und
 * dadurch automatisch mitbewegt wird. Das Aussehen kommt komplett aus dem Resource Pack
 * (Item-Modell per {@code item_model}-Komponente). Pro Tick wird nur die Drehung an den
 * Koerper angepasst; die Schlag-Animation laeuft ueber die Client-Interpolation der
 * Display-Entities und kostet den Server so gut wie nichts.
 */
final class WingInstance {

    enum Side { LEFT, RIGHT }

    private final CosmeticsPlugin plugin;
    private final NamespacedKey markerKey;
    private final Player player;
    private final WingType type;

    private ItemDisplay left;
    private ItemDisplay right;

    private float lastYaw = Float.NaN;
    private int flapTick;
    private boolean flapClosed;
    private boolean lastFlying;
    private int respawnDelay;

    WingInstance(CosmeticsPlugin plugin, NamespacedKey markerKey, Player player, WingType type) {
        this.plugin = plugin;
        this.markerKey = markerKey;
        this.player = player;
        this.type = type;
    }

    WingType type() {
        return type;
    }

    Player player() {
        return player;
    }

    void tick(WingSettings s) {
        if (respawnDelay > 0) {
            respawnDelay--;
            return;
        }
        if (!shouldShow(s)) {
            despawn();
            return;
        }
        if (!isMounted()) {
            // z.B. nach Teleport (Paper wirft Passagiere ab) oder beim ersten Tick
            despawn();
            spawn(s);
        }
        syncRotation(s);
        animate(s);
    }

    /** Fluegel kurz entfernen; sie erscheinen nach {@code ticks} Ticks wieder. */
    void hideFor(int ticks) {
        despawn();
        respawnDelay = Math.max(respawnDelay, ticks);
    }

    void despawn() {
        if (left != null) {
            left.remove();
            left = null;
        }
        if (right != null) {
            right.remove();
            right = null;
        }
        lastYaw = Float.NaN;
    }

    // ------------------------------------------------------------------

    private boolean shouldShow(WingSettings s) {
        if (!player.isOnline() || player.isDead() || player.getGameMode() == GameMode.SPECTATOR) {
            return false;
        }
        if (player.isInvisible() || player.hasPotionEffect(PotionEffectType.INVISIBILITY) || player.isSleeping()) {
            return false;
        }
        return !(s.hideWhileSwimming() && (player.isSwimming() || player.getPose() == Pose.SWIMMING));
    }

    private boolean isMounted() {
        return isMountedOnPlayer(left) && isMountedOnPlayer(right);
    }

    private boolean isMountedOnPlayer(ItemDisplay display) {
        if (display == null || !display.isValid()) {
            return false;
        }
        Entity vehicle = display.getVehicle();
        return vehicle != null && vehicle.getUniqueId().equals(player.getUniqueId());
    }

    private void spawn(WingSettings s) {
        float yaw = currentYaw(s);
        Location loc = player.getLocation();
        loc.setYaw(yaw);
        loc.setPitch(0);

        flapTick = 0;
        flapClosed = false;
        lastFlying = isFlying();

        left = spawnPart(loc, type.leftModel(), transformation(Side.LEFT, s.restAngle(), s));
        right = spawnPart(loc, type.rightModel(), transformation(Side.RIGHT, s.restAngle(), s));
        player.addPassenger(left);
        player.addPassenger(right);

        if (!s.visibleToSelf()) {
            player.hideEntity(plugin, left);
            player.hideEntity(plugin, right);
        }
        lastYaw = yaw;
    }

    private ItemDisplay spawnPart(Location loc, NamespacedKey model, Transformation transformation) {
        return loc.getWorld().spawn(loc, ItemDisplay.class, d -> {
            d.setPersistent(false); // wird nie in die Welt gespeichert
            d.getPersistentDataContainer().set(markerKey, PersistentDataType.BYTE, (byte) 1);
            d.setItemStack(modelItem(model));
            d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.NONE);
            d.setBillboard(Display.Billboard.FIXED);
            d.setShadowRadius(0f);
            d.setShadowStrength(0f);
            d.setTeleportDuration(2); // weiche Drehung
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(0);
            d.setTransformation(transformation);
        });
    }

    static ItemStack modelItem(NamespacedKey model) {
        ItemStack item = new ItemStack(Material.PAPER);
        ItemMeta meta = item.getItemMeta();
        meta.setItemModel(model);
        item.setItemMeta(meta);
        return item;
    }

    private float currentYaw(WingSettings s) {
        return s.useBodyYaw() ? player.getBodyYaw() : player.getLocation().getYaw();
    }

    private void syncRotation(WingSettings s) {
        float yaw = currentYaw(s);
        if (!Float.isNaN(lastYaw) && Math.abs(wrapDegrees(yaw - lastYaw)) < 0.75f) {
            return;
        }
        left.setRotation(yaw, 0);
        right.setRotation(yaw, 0);
        lastYaw = yaw;
    }

    private boolean isFlying() {
        return player.isGliding() || player.isFlying();
    }

    private void animate(WingSettings s) {
        boolean flying = isFlying();
        if (flying != lastFlying) {
            lastFlying = flying;
            flapTick = 0; // sofort auf neues Tempo umschalten
        }
        int period = flying ? s.flyingFlapPeriodTicks() : s.flapPeriodTicks();
        float amplitude = flying ? s.flyingFlapAmplitude() : s.flapAmplitude();
        int half = Math.max(1, period / 2);

        if (flapTick % half == 0) {
            flapClosed = !flapClosed;
            float angle = s.restAngle() + (flapClosed ? amplitude : 0f);
            applyAnimated(left, transformation(Side.LEFT, angle, s), half);
            applyAnimated(right, transformation(Side.RIGHT, angle, s), half);
        }
        flapTick++;
    }

    private static void applyAnimated(ItemDisplay display, Transformation transformation, int durationTicks) {
        // Die Interpolation startet auf dem Client nur, wenn sich der Start-Delay "aendert".
        // -1 -> 0 im selben Tick sorgt dafuer, dass der Wert sicher mitgeschickt wird.
        display.setInterpolationDelay(-1);
        display.setInterpolationDelay(0);
        display.setInterpolationDuration(durationTicks);
        display.setTransformation(transformation);
    }

    /**
     * Baut die Transformation eines Fluegels.
     *
     * <p>Die Fluegelwurzel liegt im Modell bei (8,8,8) = Drehpunkt. Der Item-Display-Renderer
     * dreht Items um 180 Grad, daher zeigt der "linke" Modell-Fluegel (+X im Modell) im
     * Entity-Raum nach -X. Hinten ist im Entity-Raum -Z (Spieler schaut bei Yaw 0 nach +Z).
     */
    static Transformation transformation(Side side, float angleDeg, WingSettings s) {
        float sweepSign = side == Side.LEFT ? -1f : 1f;
        if (s.invertSweep()) {
            sweepSign = -sweepSign;
        }
        float x = side == Side.LEFT ? -s.spreadX() : s.spreadX();
        Quaternionf rotation = new Quaternionf().rotateY((float) Math.toRadians(angleDeg) * sweepSign);
        return new Transformation(
                new Vector3f(x, s.offsetY(), s.offsetZ()),
                rotation,
                new Vector3f(s.scale(), s.scale(), s.scale()),
                new Quaternionf());
    }

    private static float wrapDegrees(float deg) {
        deg %= 360f;
        if (deg >= 180f) {
            deg -= 360f;
        }
        if (deg < -180f) {
            deg += 360f;
        }
        return deg;
    }
}
