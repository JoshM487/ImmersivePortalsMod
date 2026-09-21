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


# 26.3 moved the GPU abstraction from Blaze3D into RenderPearl. Most of these
# are package-only moves, so migrate them across the full modern source tree
# before tackling the smaller set of signature/semantic changes.
source_roots = [
    root / "common/src/main/java",
    root / "fabric/src/main/java",
]
moves = {
    "com.mojang.blaze3d.GpuFormat": "com.mojang.renderpearl.api.GpuFormat",
    "com.mojang.blaze3d.IndexType": "com.mojang.renderpearl.api.pipeline.IndexType",
    "com.mojang.blaze3d.PrimitiveTopology": "com.mojang.renderpearl.api.pipeline.PrimitiveTopology",
    "com.mojang.blaze3d.buffers.GpuBufferSlice": "com.mojang.renderpearl.api.buffers.GpuBufferSlice",
    "com.mojang.blaze3d.buffers.GpuBuffer": "com.mojang.renderpearl.api.buffers.GpuBuffer",
    "com.mojang.blaze3d.buffers.GpuFence": "com.mojang.renderpearl.api.commands.GpuFence",
    "com.mojang.blaze3d.opengl.": "com.mojang.renderpearl.backend.opengl.",
    "com.mojang.blaze3d.textures.": "com.mojang.renderpearl.api.textures.",

    "com.mojang.blaze3d.pipeline.BindGroupLayout": "com.mojang.renderpearl.api.pipeline.BindGroupLayout",
    "com.mojang.blaze3d.pipeline.BlendEquation": "com.mojang.renderpearl.api.pipeline.BlendEquation",
    "com.mojang.blaze3d.pipeline.BlendFunction": "com.mojang.renderpearl.api.pipeline.BlendFunction",
    "com.mojang.blaze3d.pipeline.CompiledRenderPipeline": "com.mojang.renderpearl.api.pipeline.CompiledRenderPipeline",
    "com.mojang.blaze3d.pipeline.DepthStencilState": "com.mojang.renderpearl.api.pipeline.DepthStencilState",
    "com.mojang.blaze3d.pipeline.RenderPipeline": "com.mojang.renderpearl.api.pipeline.RenderPipeline",

    "com.mojang.blaze3d.platform.BlendFactor": "com.mojang.renderpearl.api.pipeline.BlendFactor",
    "com.mojang.blaze3d.platform.BlendOp": "com.mojang.renderpearl.api.pipeline.BlendOp",
    "com.mojang.blaze3d.platform.CompareOp": "com.mojang.renderpearl.api.pipeline.CompareOp",
    "com.mojang.blaze3d.platform.PolygonMode": "com.mojang.renderpearl.api.pipeline.PolygonMode",

    "com.mojang.blaze3d.shaders.GpuDebugOptions": "com.mojang.renderpearl.api.device.GpuDebugOptions",
    "com.mojang.blaze3d.shaders.ShaderSource": "com.mojang.renderpearl.api.pipeline.ShaderSource",
    "com.mojang.blaze3d.shaders.ShaderType": "com.mojang.renderpearl.api.pipeline.ShaderType",
    "com.mojang.blaze3d.shaders.UniformType": "com.mojang.renderpearl.api.pipeline.UniformType",

    "com.mojang.blaze3d.systems.CommandEncoderBackend": "com.mojang.renderpearl.backend.api.CommandEncoderBackend",
    "com.mojang.blaze3d.systems.CommandEncoder": "com.mojang.renderpearl.api.commands.CommandEncoder",
    "com.mojang.blaze3d.systems.DeviceFeatures": "com.mojang.renderpearl.api.device.DeviceFeatures",
    "com.mojang.blaze3d.systems.DeviceInfo": "com.mojang.renderpearl.api.device.DeviceInfo",
    "com.mojang.blaze3d.systems.DeviceLimits": "com.mojang.renderpearl.api.device.DeviceLimits",
    "com.mojang.blaze3d.systems.DeviceType": "com.mojang.renderpearl.api.device.DeviceType",
    "com.mojang.blaze3d.systems.GpuDeviceBackend": "com.mojang.renderpearl.backend.api.GpuDeviceBackend",
    "com.mojang.blaze3d.systems.GpuDevice": "com.mojang.renderpearl.api.device.GpuDevice",
    "com.mojang.blaze3d.systems.GpuQueryPool": "com.mojang.renderpearl.api.commands.GpuQueryPool",
    "com.mojang.blaze3d.systems.GpuQuery": "com.mojang.renderpearl.api.commands.GpuQuery",
    "com.mojang.blaze3d.systems.RenderPassDescriptor": "com.mojang.renderpearl.api.commands.RenderPassDescriptor",
    "com.mojang.blaze3d.systems.RenderPass": "com.mojang.renderpearl.api.commands.RenderPass",

    "com.mojang.blaze3d.vertex.VertexFormatElement": "com.mojang.renderpearl.api.vertex.VertexFormatElement",
    "com.mojang.blaze3d.vertex.VertexFormat": "com.mojang.renderpearl.api.vertex.VertexFormat",

    "net.minecraft.world.level.levelgen.DensityFunctions": "net.minecraft.world.level.levelgen.densityfunction.DensityFunctions",
    "net.minecraft.world.level.levelgen.DensityFunction": "net.minecraft.world.level.levelgen.densityfunction.DensityFunction",
    "net.minecraft.world.level.block.RedStoneWireBlock": "net.minecraft.world.level.block.RedstoneWireBlock",
    "RedStoneWireBlock": "RedstoneWireBlock",
}
for src_root in source_roots:
    if not src_root.exists():
        continue
    for p in src_root.rglob("*.java"):
        text = p.read_text(encoding="utf-8")
        new_text = text
        for old, new in moves.items():
            new_text = new_text.replace(old, new)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")


# Additional 26.3 render API changes that preserve behavior.
for src_root in source_roots:
    if not src_root.exists():
        continue
    for p in src_root.rglob("*.java"):
        text = p.read_text(encoding="utf-8")
        new_text = text

        new_text = new_text.replace(
            "com.mojang.blaze3d.pipeline.ColorTargetState",
            "com.mojang.renderpearl.api.pipeline.ColorTargetState"
        )
        new_text = new_text.replace(
            ".withBindGroupLayout(BindGroupLayouts.MATRICES_PROJECTION)",
            ".withBindGroupLayout(BindGroupLayouts.PROJECTION)\n"
            "                .withBindGroupLayout(BindGroupLayouts.DYNAMIC_TRANSFORMS)"
        )
        new_text = new_text.replace(
            ".gameRenderer.gameRenderState().useShaderTransparency()",
            ".useShaderTransparency()"
        )
        # The previous replacement yields mc.useShaderTransparency()/client.useShaderTransparency();
        # normalize to the static 26.3 home.
        new_text = re.sub(
            r"\\b(?:mc|client)\\.useShaderTransparency\\(\\)",
            "net.minecraft.client.Minecraft.useShaderTransparency()",
            new_text
        )

        # RenderPass sampler bindings became generic uniform bindings.
        new_text = new_text.replace(".bindTexture(", ".setUniform(")

        # RenderPass now consumes a CompiledRenderPipeline. Wrap simple one-line pipeline
        # submissions through RenderSystem's cache, which is the vanilla 26.3 path.
        new_text = re.sub(
            r"(\\b\\w+\\.setPipeline\\()([^;\\n]+)(\\);)",
            lambda m: (
                m.group(0) if "getCompiledPipeline(" in m.group(2)
                else m.group(1) + "RenderSystem.getCompiledPipeline(" + m.group(2) + ")" + m.group(3)
            ),
            new_text
        )

        # Own mixin class names intentionally keep Mojang's old spelling in their filenames.
        new_text = new_text.replace(
            "class MixinRedstoneWireBlockSeamAuthority",
            "class MixinRedStoneWireBlockSeamAuthority"
        )
        new_text = new_text.replace(
            "class MixinRedstoneWireBlockSeamSignal",
            "class MixinRedStoneWireBlockSeamSignal"
        )

        if new_text != text:
            p.write_text(new_text, encoding="utf-8")


# Direct 26.3 call-shape migrations.
for src_root in source_roots:
    if not src_root.exists():
        continue
    for p in src_root.rglob("*.java"):
        text = p.read_text(encoding="utf-8")
        new_text = text

        # Shader transparency is a static Minecraft query again in 26.3.
        new_text = new_text.replace("client.useShaderTransparency()", "Minecraft.useShaderTransparency()")
        new_text = new_text.replace("mc.useShaderTransparency()", "Minecraft.useShaderTransparency()")

        # PoseStack renamed the quaternion operation to rotate(Quaternionfc).
        new_text = re.sub(r"(\b\w+)\.mulPose\(([^;\n]*toMcQuaternion\(\)[^;\n]*)\)",
                          r"\1.rotate(\2)", new_text)
        new_text = re.sub(r"(\b\w+)\.mulPose\(([^;\n]*Quaternion[^;\n]*)\)",
                          r"\1.rotate(\2)", new_text)

        # 26.3 TextureTarget takes explicit color/depth formats.
        new_text = new_text.replace(
            ", true, GpuFormat.RGBA8_UNORM)",
            ", GpuFormat.RGBA8_UNORM, GpuFormat.D32_FLOAT)"
        )
        new_text = new_text.replace(
            ", false, GpuFormat.RGBA8_UNORM)",
            ", GpuFormat.RGBA8_UNORM, null)"
        )
        new_text = new_text.replace(
            ", true, com.mojang.renderpearl.api.GpuFormat.RGBA8_UNORM)",
            ", com.mojang.renderpearl.api.GpuFormat.RGBA8_UNORM, com.mojang.renderpearl.api.GpuFormat.D32_FLOAT)"
        )
        new_text = new_text.replace(
            ", false, com.mojang.renderpearl.api.GpuFormat.RGBA8_UNORM)",
            ", com.mojang.renderpearl.api.GpuFormat.RGBA8_UNORM, null)"
        )

        # RenderPass.setPipeline takes a compiled pipeline in 26.3. The previous
        # generic regex intentionally missed nested expressions; cover the known
        # portal call shapes explicitly and then a conservative one-line fallback.
        known_pipeline_exprs = [
            "PORTAL_STRAIGHT_COPY",
            "sel.pipeline()",
            "PortalRenderTypes.portalCompositeBlit()",
            "PortalRenderTypes.portalScreenDepthClear()",
            "pipeline",
        ]
        for expr in known_pipeline_exprs:
            new_text = new_text.replace(
                f"pass.setPipeline({expr});",
                f"pass.setPipeline(RenderSystem.getCompiledPipeline({expr}));"
            )

        if new_text != text:
            p.write_text(new_text, encoding="utf-8")

# 26.3 RenderPearl keeps the OpenGL backend package-private behind FrontendGpuDevice.
# Restore only the access Immersive Portals needs for live FBO/stencil resolution.
aw = root / "common/src/main/resources/seamlessportals.accesswidener"
aws = aw.read_text(encoding="utf-8")
extra_aw = [
    "accessible class com/mojang/renderpearl/backend/opengl/GlDevice",
    "accessible field com/mojang/renderpearl/frontend/FrontendGpuDevice backend Lcom/mojang/renderpearl/backend/api/GpuDeviceBackend;",
]
for line in extra_aw:
    if line not in aws:
        aws += "\n" + line
aw.write_text(aws + ("\n" if not aws.endswith("\n") else ""), encoding="utf-8")

# GpuDevice is now an interface backed by FrontendGpuDevice; reach the widened backend field.
for src_root in source_roots:
    if not src_root.exists():
        continue
    for p in src_root.rglob("*.java"):
        text = p.read_text(encoding="utf-8")
        new_text = text.replace(
            "RenderSystem.getDevice().backend",
            "((com.mojang.renderpearl.frontend.FrontendGpuDevice) RenderSystem.getDevice()).backend"
        )
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")

# 26.3's OIT/framegraph no longer has the 26.2 decomposed stage-target model.
# Use the port's existing full LevelRenderer pipeline path for all destination renders.
swrc = root / "common/src/main/java/qouteall/imm_ptl/core/render/SecondaryWorldRenderCore.java"
sw = swrc.read_text(encoding="utf-8")
method_start = sw.index("    public static void renderDestWorld(")
full_pipeline_marker = sw.index("    // migration/IRIS_SHADERS_ON_DESIGN.md", method_start)
replacement = """    public static void renderDestWorld(
        ClientLevel destLevel, LevelRenderer destRenderer, Camera newCamera, int renderDistance,
        ClientLevel sourceLevel, Camera sourceCamera
    ) {
        renderDestWorldFullPipeline(
            destLevel, destRenderer, newCamera, renderDistance, sourceLevel, sourceCamera
        );
    }

"""
sw = sw[:method_start] + replacement + sw[full_pipeline_marker:]
swrc.write_text(sw, encoding="utf-8")

# 26.3 removed/reworked the old noise-router/worldgen configuration APIs. Alternate
# skyland/chaos dimensions are peripheral to portal rendering, so keep the first 26.3
# release focused on core portals and dimension-stack behavior.
import shutil, json
for rel in [
    "common/src/main/java/qouteall/imm_ptl/peripheral/alternate_dimension",
    "common/src/main/java/qouteall/imm_ptl/peripheral/mixin/common/alternate_dimension",
    "common/src/main/java/qouteall/imm_ptl/peripheral/mixin/client/alternate_dimension",
]:
    d = root / rel
    if d.exists():
        shutil.rmtree(d)

periph = root / "common/src/main/java/qouteall/imm_ptl/peripheral/PeripheralModMain.java"
pt = periph.read_text(encoding="utf-8")
pt = re.sub(
    r"\s*qouteall\.imm_ptl\.peripheral\.alternate_dimension\.FormulaGenerator\.init\(\);",
    "",
    pt
)
pt = re.sub(
    r"\s*qouteall\.imm_ptl\.peripheral\.alternate_dimension\.AlternateDimensions\.init\(\);",
    "",
    pt
)
pt = re.sub(
    r"\s*qouteall\.dimlib\.api\.DimensionAPI\.suppressExperimentalWarningForNamespace\(\s*\"immersive_portals\"\s*\);",
    "",
    pt
)

def replace_method_with_noop(src, marker):
    start = src.index(marker)
    brace = src.index("{", start)
    depth = 0
    end = None
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Could not find end of method {marker}")
    header = src[start:brace + 1]
    return src[:start] + header + "\n        // Disabled on 26.3: legacy alternate-dimension worldgen API was removed.\n    }" + src[end:]

pt = replace_method_with_noop(pt, "    public static void registerChunkGenerators(")
pt = replace_method_with_noop(pt, "    public static void registerBiomeSources(")
periph.write_text(pt, encoding="utf-8")

mix_path = root / "common/src/main/resources/seamlessportals-ip-peripheral.mixins.json"
mix = json.loads(mix_path.read_text(encoding="utf-8"))
for key in ("mixins", "client"):
    mix[key] = [x for x in mix.get(key, []) if "alternate_dimension" not in x]
mix_path.write_text(json.dumps(mix, indent=2) + "\n", encoding="utf-8")
print("Applied Minecraft 26.3 baseline patch")
