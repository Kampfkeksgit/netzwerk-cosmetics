base {
    archivesName.set("NetzwerkCosmetics-Bungee")
}

dependencies {
    compileOnly("net.md-5:bungeecord-api:1.21-R0.4")
}

// Baut mit dem JDK, das Gradle ausfuehrt (Java 25), erzeugt aber Java-21-Bytecode
tasks.withType<JavaCompile>().configureEach {
    options.release.set(21)
}

val pluginVersion = project.version.toString()

tasks.processResources {
    inputs.property("version", pluginVersion)
    filesMatching("bungee.yml") {
        expand("version" to pluginVersion)
    }
}
