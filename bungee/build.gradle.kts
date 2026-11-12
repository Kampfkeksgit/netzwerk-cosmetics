base {
    archivesName.set("NetzwerkCosmetics-Bungee")
}

dependencies {
    compileOnly("net.md-5:bungeecord-api:1.21-R0.4")
}

java {
    toolchain.languageVersion.set(JavaLanguageVersion.of(21))
}

tasks.processResources {
    filesMatching("bungee.yml") {
        expand("version" to project.version)
    }
}
