base {
    archivesName.set("NetzwerkCosmetics-Paper")
}

dependencies {
    compileOnly("io.papermc.paper:paper-api:26.3.build.249-stable")
}

java {
    toolchain.languageVersion.set(JavaLanguageVersion.of(25))
}

// Packt ../resourcepack als resourcepack.zip in die Plugin-JAR (wird beim Start entpackt)
val zipResourcePack by tasks.registering(Zip::class) {
    group = "build"
    description = "Packt das Resource Pack"
    from(rootProject.layout.projectDirectory.dir("resourcepack"))
    archiveFileName.set("resourcepack.zip")
    destinationDirectory.set(layout.buildDirectory.dir("pack"))
    isPreserveFileTimestamps = false   // gleiche Dateien => gleicher SHA-1
    isReproducibleFileOrder = true
}

tasks.processResources {
    from(zipResourcePack)
    filesMatching("plugin.yml") {
        expand("version" to project.version)
    }
}
