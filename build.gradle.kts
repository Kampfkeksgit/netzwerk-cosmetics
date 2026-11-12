plugins {
    java
}

group = "de.netzwerk"
version = "1.0.0"

repositories {
    mavenCentral()
    maven("https://repo.papermc.io/repository/maven-public/")
}

dependencies {
    compileOnly("io.papermc.paper:paper-api:1.21.11-R0.1-SNAPSHOT")
}

java {
    toolchain.languageVersion.set(JavaLanguageVersion.of(21))
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.release.set(21)
}

// Packt den Ordner ./resourcepack als resourcepack.zip.
// Die ZIP landet in der Plugin-JAR (wird beim Start in plugins/NetzwerkCosmetics/ entpackt)
// und zusaetzlich unter build/resourcepack.zip, falls du sie extern hosten willst.
val zipResourcePack by tasks.registering(Zip::class) {
    group = "build"
    description = "Packt das Resource Pack"
    from(layout.projectDirectory.dir("resourcepack"))
    archiveFileName.set("resourcepack.zip")
    destinationDirectory.set(layout.buildDirectory)
    isPreserveFileTimestamps = false   // gleiche Dateien => gleicher SHA-1
    isReproducibleFileOrder = true
}

tasks.processResources {
    dependsOn(zipResourcePack)
    from(zipResourcePack)
    filesMatching("plugin.yml") {
        expand("version" to project.version)
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.addAll(listOf("-Xlint:deprecation", "-Xlint:removal"))
}
