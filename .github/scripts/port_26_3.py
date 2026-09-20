#!/usr/bin/env python3
from pathlib import Path
import re, sys

root = Path(sys.argv[1])

def replace(path, old, new):
    p = root / path
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"missing text in {path}: {old!r}")
    p.write_text(s.replace(old, new), encoding="utf-8")

def regex(path, pattern, replacement):
    p = root / path
    s = p.read_text(encoding="utf-8")
    ns, n = re.subn(pattern, replacement, s, flags=re.M)
    if n == 0:
        raise SystemExit(f"pattern did not match in {path}: {pattern}")
    p.write_text(ns, encoding="utf-8")

# Core Minecraft/Fabric toolchain.
gp = root / "gradle.properties"
s = gp.read_text(encoding="utf-8")
updates = {
    "minecraft_version": "26.3",
    "minecraft_version_range": "[26.3,26.4)",
    "java_version": "25",
    "fabric_version": "0.161.0+26.3",
    "fabric_loader_version": "0.19.5",
    "neo_form_version": "26.3-1",
    "sodium_version": "mc26.3-0.9.2-fabric",
    "iris_version": "1.11.6+26.3-fabric",
    "cloth_config_version": "26.3.158",
}
for key, value in updates.items():
    s, n = re.subn(rf"^{re.escape(key)}=.*$", f"{key}={value}", s, flags=re.M)
    if not n:
        raise SystemExit(f"missing gradle property {key}")

# CI uses Temurin 25 from setup-java. Remove the original developer-machine-only Zulu pin.
s = re.sub(r"^org\.gradle\.java\.installations\.paths=.*\n?", "", s, flags=re.M)
s = re.sub(r"^org\.gradle\.java\.installations\.auto-download=.*\n?", "", s, flags=re.M)
s = re.sub(r"^jdkVendor=.*\n?", "", s, flags=re.M)
gp.write_text(s, encoding="utf-8")

# Loom/Gradle versions recommended for 26.3.
regex("build.gradle", r"id 'net\.fabricmc\.fabric-loom' version '[^']+' apply false",
      "id 'net.fabricmc.fabric-loom' version '1.17.21' apply false")
regex("gradle/wrapper/gradle-wrapper.properties",
      r"^distributionUrl=.*$",
      r"distributionUrl=https\\://services.gradle.org/distributions/gradle-9.6.0-bin.zip")

# Current 26.3 Mod Menu compile target.
regex("fabric/build.gradle",
      r'implementation "com\.terraformersmc:modmenu:[^"]+"',
      'implementation "com.terraformersmc:modmenu:21.0.0-beta.1"')

# Fabric metadata must not claim 26.2.
replace("fabric/src/main/resources/fabric.mod.json",
        '"minecraft": ">=26.2",',
        '"minecraft": "26.3",')
replace("fabric/src/main/resources/fabric.mod.json",
        '"cloth-config": ">=26.2"',
        '"cloth-config": ">=26.3"')


# 26.3 renderer internals changed. Remove 26.2-only wideners first; if source still
# needs an access, the Java compiler will point at the replacement API explicitly.
aw = root / "common/src/main/resources/seamlessportals.accesswidener"
aws = aw.read_text(encoding="utf-8")
for dead_entry in [
    "accessible method net/minecraft/client/renderer/RenderPipelines register (Lcom/mojang/blaze3d/pipeline/RenderPipeline;)Lcom/mojang/blaze3d/pipeline/RenderPipeline;\n",
    "accessible class com/mojang/blaze3d/opengl/GlDevice\n",
    "accessible field com/mojang/blaze3d/systems/GpuDevice backend Lcom/mojang/blaze3d/systems/GpuDeviceBackend;\n",
]:
    aws = aws.replace(dead_entry, "")
aw.write_text(aws, encoding="utf-8")

print("Applied Minecraft 26.3 baseline patch")
