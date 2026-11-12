base {
    archivesName.set("NetzwerkCosmetics-Paper")
}

dependencies {
    compileOnly("io.papermc.paper:paper-api:26.3.build.249-stable")
}

// Baut mit dem JDK, das Gradle ausfuehrt (Java 25), erzeugt aber Java-25-Bytecode
tasks.withType<JavaCompile>().configureEach {
    options.release.set(25)
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

val pluginVersion = project.version.toString()

tasks.processResources {
    inputs.property("version", pluginVersion)
    from(zipResourcePack)
    filesMatching("plugin.yml") {
        expand("version" to pluginVersion)
    }
}
