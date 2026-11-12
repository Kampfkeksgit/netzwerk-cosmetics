package de.netzwerk.cosmetics.gui;

import net.kyori.adventure.key.Key;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;

/**
 * Baut Inventar-Titel, die ein Hintergrundbild aus dem Resource Pack zeigen.
 *
 * <p>Trick: Der Titel eines Inventars ist normaler Text. Im Resource Pack ist ein eigener Font
 * definiert, in dem ein Zeichen (z.B. {@code }) ein komplettes GUI-Bild ist
 * ({@code assets/cosmetics/font/gui.json}). Mit "Leerzeichen" negativer Breite
 * ({@code assets/cosmetics/font/space.json}) wird der Cursor so verschoben, dass das Bild
 * genau auf dem Truhen-Hintergrund liegt. Danach geht es zurueck an die normale Titelposition.
 */
public final class GuiFont {

    public static final Key SPACE_FONT = Key.key("cosmetics", "space");
    public static final Key GUI_FONT = Key.key("cosmetics", "gui");

    /** Breite (in GUI-Pixeln) des Truhen-Hintergrunds. Bitmap-Glyphen haben +1 Abstand. */
    public static final int CHEST_WIDTH = 176;
    /** Der Titel wird vom Spiel bei x=8 gezeichnet. */
    public static final int TITLE_X = 8;

    public static final char WARDROBE = '';

    private GuiFont() {
    }

    /**
     * Verschiebt den Text-Cursor um {@code pixels} (negativ = nach links).
     * Zerlegt die Zahl in Zweierpotenzen (space.json: .. = -1,-2,-4,... / .. = +1,+2,+4,...).
     */
    public static Component shift(int pixels) {
        if (pixels == 0) {
            return Component.empty();
        }
        char base = pixels < 0 ? '' : '';
        int remaining = Math.abs(pixels);
        StringBuilder sb = new StringBuilder();
        for (int bit = 9; bit >= 0; bit--) {
            int value = 1 << bit;
            while (remaining >= value) {
                sb.append((char) (base + bit));
                remaining -= value;
            }
        }
        return Component.text(sb.toString()).font(SPACE_FONT);
    }

    /**
     * Titel mit Vollbild-Hintergrund ({@code glyph} = 176 px breit) plus normalem Titeltext.
     * Das Bild muss weiss eingefaerbt werden, sonst faerbt Minecraft es grau (Standard-Titelfarbe).
     */
    public static Component backgroundTitle(char glyph, Component title) {
        int glyphAdvance = CHEST_WIDTH + 1;
        return Component.text()
                .append(shift(-TITLE_X))
                .append(Component.text(glyph).font(GUI_FONT).color(NamedTextColor.WHITE))
                .append(shift(-(glyphAdvance - TITLE_X)))
                .append(title)
                .build();
    }
}
