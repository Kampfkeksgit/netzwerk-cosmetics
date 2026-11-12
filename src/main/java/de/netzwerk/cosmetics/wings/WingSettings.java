package de.netzwerk.cosmetics.wings;

import java.util.Locale;
import org.bukkit.configuration.file.FileConfiguration;

/** Darstellung und Animation der Fluegel (config.yml: wing-settings). */
public record WingSettings(
        float scale,
        float offsetY,
        float offsetZ,
        float spreadX,
        float restAngle,
        float flapAmplitude,
        int flapPeriodTicks,
        float flyingFlapAmplitude,
        int flyingFlapPeriodTicks,
        boolean useBodyYaw,
        boolean invertSweep,
        boolean visibleToSelf,
        boolean hideWhileSwimming
) {

    public static WingSettings fromConfig(FileConfiguration c) {
        String p = "wing-settings.";
        return new WingSettings(
                (float) c.getDouble(p + "scale", 0.75),
                (float) c.getDouble(p + "offset-y", -0.42),
                (float) c.getDouble(p + "offset-z", -0.20),
                (float) c.getDouble(p + "spread-x", 0.06),
                (float) c.getDouble(p + "rest-angle", 20),
                (float) c.getDouble(p + "flap-amplitude", 18),
                Math.max(2, c.getInt(p + "flap-period-ticks", 40)),
                (float) c.getDouble(p + "flying-flap-amplitude", 35),
                Math.max(2, c.getInt(p + "flying-flap-period-ticks", 10)),
                !"HEAD".equals(c.getString(p + "rotation-source", "BODY").toUpperCase(Locale.ROOT)),
                c.getBoolean(p + "invert-sweep", false),
                c.getBoolean(p + "visible-to-self", true),
                c.getBoolean(p + "hide-while-swimming", true)
        );
    }
}
