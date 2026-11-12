plugins {
    base
}

allprojects {
    group = "de.netzwerk"
    version = "1.2.0"
}

subprojects {
    apply(plugin = "java")

    repositories {
        mavenCentral()
        maven("https://repo.papermc.io/repository/maven-public/")
    }

    tasks.withType<JavaCompile>().configureEach {
        options.encoding = "UTF-8"
        options.compilerArgs.addAll(listOf("-Xlint:deprecation", "-Xlint:removal"))
    }
}

// Sammelt beide Plugin-JARs und das Resource Pack in dist/ (wird mit ins Repo committet,
// damit Server per "git pull" immer die aktuellen JARs bekommen). Feste Dateinamen ohne
// Versionsnummer, damit beim Kopieren in plugins/ nie zwei Versionen nebeneinander liegen.
val dist by tasks.registering(Copy::class) {
    group = "build"
    description = "Kopiert alle fertigen Dateien nach dist/"
    dependsOn(":paper:jar", ":bungee:jar", ":paper:zipResourcePack")
    from(project(":paper").tasks.named("jar"))
    from(project(":bungee").tasks.named("jar"))
    from(project(":paper").tasks.named("zipResourcePack"))
    rename { it.replace(Regex("-\\d+\\.\\d+\\.\\d+"), "") }
    into(layout.projectDirectory.dir("dist"))
    doLast {
        val zip = destinationDir.resolve("resourcepack.zip")
        val sha1 = java.security.MessageDigest.getInstance("SHA-1").digest(zip.readBytes())
            .joinToString("") { "%02x".format(it) }
        destinationDir.resolve("resourcepack.sha1").writeText(sha1 + "\n")
        println("Resource Pack SHA-1: $sha1")
    }
}

tasks.named("build") {
    dependsOn(dist)
}
