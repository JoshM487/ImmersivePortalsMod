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
            "com.mojang.blaze3d.systems.RenderSystem.getDevice().backend",
            "((com.mojang.renderpearl.frontend.FrontendGpuDevice) com.mojang.blaze3d.systems.RenderSystem.getDevice()).backend"
        )
        new_text = new_text.replace(
            "RenderSystem.getDevice().backend",
            "((com.mojang.renderpearl.frontend.FrontendGpuDevice) RenderSystem.getDevice()).backend"
        )
        new_text = new_text.replace(
            "com.mojang.blaze3d.systems.((com.mojang.renderpearl.frontend.FrontendGpuDevice) RenderSystem.getDevice()).backend",
            "((com.mojang.renderpearl.frontend.FrontendGpuDevice) com.mojang.blaze3d.systems.RenderSystem.getDevice()).backend"
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


# --- 26.3 production cleanup / API reconciliation ---
# The 26.2 hand-port carries a large suite of one-off render probes used while developing
# its Iris/stencil path. They are not production features and several reach private 26.2
# OpenGL internals that RenderPearl intentionally hides in 26.3.
diagnostic_files = [
    "common/src/main/java/qouteall/imm_ptl/core/compat/iris_compatibility/ShaderpackViewsProbe.java",
    "common/src/main/java/qouteall/imm_ptl/core/render/TeleportFlashProbe.java",
    "common/src/main/java/qouteall/imm_ptl/core/render/StageCensusProbe.java",
    "common/src/main/java/qouteall/imm_ptl/core/render/DrawCallTrace.java",
    "common/src/main/java/com/warwa/seamlessportals/render/SeamHandStageDiff.java",
    "common/src/main/java/com/warwa/seamlessportals/render/SeamDestContentProbe.java",
    "common/src/main/java/com/warwa/seamlessportals/render/SeamHandLocator.java",
    "common/src/main/java/com/warwa/seamlessportals/render/SeamHandSubmitTap.java",
    "common/src/main/java/com/warwa/seamlessportals/render/SeamHandInLevelProbe.java",
]
for rel in diagnostic_files:
    p = root / rel
    if p.exists():
        p.unlink()

# Strip mixin entries that target the removed development probes.
for mixfile in (root / "common/src/main/resources").glob("*.mixins.json"):
    try:
        data = json.loads(mixfile.read_text(encoding="utf-8"))
    except Exception:
        continue
    changed = False
    for key in ("mixins", "client", "server"):
        arr = data.get(key)
        if isinstance(arr, list):
            filtered = [
                x for x in arr
                if not any(tag in x for tag in (
                    "ShaderpackViewsProbe", "TeleportFlashProbe", "StageCensusProbe",
                    "DrawCallTrace", "SeamHandStageDiff", "SeamDestContentProbe",
                    "SeamHandLocator", "SeamHandSubmitTap", "SeamHandInLevelProbe"
                ))
            ]
            if filtered != arr:
                data[key] = filtered
                changed = True
    if changed:
        mixfile.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

# 26.3 replaced the previous shader/fabulous query with GameRenderer's current
# improved-transparency decision.
for src_root in source_roots:
    if not src_root.exists():
        continue
    for p in src_root.rglob("*.java"):
        text = p.read_text(encoding="utf-8")
        new_text = text.replace(
            "Minecraft.useShaderTransparency()",
            "Minecraft.getInstance().gameRenderer.useImprovedTransparency()"
        )
        new_text = new_text.replace(
            "net.minecraft.client.Minecraft.useShaderTransparency()",
            "net.minecraft.client.Minecraft.getInstance().gameRenderer.useImprovedTransparency()"
        )

        # Pipeline eager-validation moved to RenderSystem's compiled-pipeline cache.
        new_text = new_text.replace(
            "if (!RenderSystem.getDevice().precompilePipeline(built).isValid()) {",
            "if (RenderSystem.getCompiledPipelineNullable(built) == null) {"
        )

        # RenderSection's old fade bookkeeping setters disappeared; the 26.3 renderer owns
        # this state internally.
        new_text = re.sub(r"^\s*\w+\.setFadeDuration\(0L\);\s*$", "", new_text, flags=re.M)
        new_text = re.sub(r"^\s*\w+\.setWasPreviouslyEmpty\(false\);\s*$", "", new_text, flags=re.M)

        # Avoid relying on an import being present after automated pipeline migration.
        new_text = new_text.replace(
            "pass.setPipeline(RenderSystem.getCompiledPipeline(",
            "pass.setPipeline(com.mojang.blaze3d.systems.RenderSystem.getCompiledPipeline("
        )

        if new_text != text:
            p.write_text(new_text, encoding="utf-8")

# BlockPos no longer has a Vec3i-copy constructor.
bps = root / "common/src/main/java/qouteall/imm_ptl/core/portal/nether_portal/BlockPortalShape.java"
if bps.exists():
    t = bps.read_text(encoding="utf-8")
    t = re.sub(
        r"new BlockPos\((directions\[[0-9]+\]\.getUnitVec3i\(\))\)",
        r"BlockPos.ZERO.offset(\1)",
        t
    )
    bps.write_text(t, encoding="utf-8")

# The custom alternate-dimension presets are disabled for the first 26.3 core-port build,
# so remove their two convenience entries from the dimension-stack UI too.
dsg = root / "common/src/main/java/qouteall/imm_ptl/peripheral/dim_stack/DimStackGuiController.java"
if dsg.exists():
    t = dsg.read_text(encoding="utf-8")
    t = re.sub(r"^import qouteall\.imm_ptl\.peripheral\.alternate_dimension\.AlternateDimensions;\n", "", t, flags=re.M)
    t = re.sub(r"^\s*entriesToAdd\.add\(new DimStackEntry\(AlternateDimensions\.[A-Z_]+\)\);\s*$", "", t, flags=re.M)
    dsg.write_text(t, encoding="utf-8")

# 26.3 uses SDL3 instead of GLFW for OpenGL window creation. Keep the stencil request,
# but express it through SDL_GL_STENCIL_SIZE (enum value 7).
gbm = root / "common/src/main/java/com/warwa/seamlessportals/mixin/client/stencil/GlBackendMixin.java"
if gbm.exists():
    t = gbm.read_text(encoding="utf-8")
    t = t.replace("import org.lwjgl.glfw.GLFW;", "import org.lwjgl.sdl.SDLVideo;")
    t = re.sub(
        r"GLFW\.glfwWindowHint\(GLFW\.GLFW_STENCIL_BITS,\s*8\);",
        "SDLVideo.SDL_GL_SetAttribute(7, 8);",
        t
    )
    gbm.write_text(t, encoding="utf-8")

# Core stencil clear: on 26.3 clear the framebuffer already bound by the active main pass.
# This avoids depending on RenderPearl's deliberately package-private GlDevice implementation.
rus = root / "common/src/main/java/qouteall/imm_ptl/core/render/renderer/RendererUsingStencil.java"
if rus.exists():
    t = rus.read_text(encoding="utf-8")
    t = t.replace("import com.mojang.renderpearl.backend.opengl.GlDevice;\n", "")
    t = t.replace("import com.mojang.renderpearl.backend.opengl.GlTextureView;\n", "")
    start_marker = "        RenderTarget mainRt = client.gameRenderer.mainRenderTarget();"
    end_marker = "\n\n        // R5 Row 2"
    if start_marker in t:
        a = t.index(start_marker)
        b = t.index(end_marker, a)
        replacement = """        // 26.3 RenderPearl hides the concrete GL backend. At this point the main
        // render target is already active, so clear the currently bound draw framebuffer's
        // stencil attachment directly and preserve all depth/color data.
        int activeDrawFbo = GlStateManager.getFrameBuffer(GL30.GL_DRAW_FRAMEBUFFER);
        if (activeDrawFbo != lastResolvedMainFbo) {
            lastResolvedMainFbo = activeDrawFbo;
            long now = System.currentTimeMillis();
            if (now - lastResolverLogMs > 1000) {
                lastResolverLogMs = now;
                Helper.log("[26.3] stencil-clear active draw FBO: " + activeDrawFbo);
            }
        }
        GlStateManager._disableScissorTest();
        GL11.glClearStencil(0);
        GL11.glClear(GL11.GL_STENCIL_BUFFER_BIT);"""
        t = t[:a] + replacement + t[b:]
    rus.write_text(t, encoding="utf-8")




# Re-create the removed diagnostics as API-compatible inert stubs. Their call sites are
# intentionally left intact, but the production 26.3 build must not depend on private
# RenderPearl backend implementation details.
def write_stub(rel, body):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")

write_stub("common/src/main/java/qouteall/imm_ptl/core/render/DrawCallTrace.java", """package qouteall.imm_ptl.core.render;
public final class DrawCallTrace {
    public static boolean armed = false;
    public static boolean capturing = false;
    private DrawCallTrace() {}
    public static void record(Object... args) {}
    public static void recordSkyState(Object... args) {}
    public static void onFrameStart(Object... args) {}
    public static void onFrameEnd(Object... args) {}
    public static String mvTop() { return ""; }
}
""")

write_stub("common/src/main/java/qouteall/imm_ptl/core/render/StageCensusProbe.java", """package qouteall.imm_ptl.core.render;
public final class StageCensusProbe {
    public static final boolean ENABLED = false;
    private StageCensusProbe() {}
    public static void passTiming(Object... args) {}
    public static void cloud(Object... args) {}
    public static void endFrame(Object... args) {}
    public static void mainClouds(Object... args) {}
    public static void markTeleport(Object... args) {}
    public static void entityRingSample(Object... args) {}
}
""")

write_stub("common/src/main/java/qouteall/imm_ptl/core/render/TeleportFlashProbe.java", """package qouteall.imm_ptl.core.render;
public final class TeleportFlashProbe {
    public static long destPassesThisFrame;
    public static long sameDimPassesThisFrame;
    public static long sameDimMaxLayerThisFrame;
    public static long sameDimEntitiesExtracted;
    public static long sameDimEntitiesSubmitted;
    public static long sameDimEntityThrow;
    public static long foldSchedMainThisFrame;
    public static long foldSchedDestThisFrame;
    public static long promoteNanosThisFrame;
    public static long destPassNanosThisFrame;
    public static long discoveryNanosThisFrame;
    public static long vanillaYieldThisFrame;
    public static long portalSkyDrawsThisFrame;
    public static long skyDrawsThisFrame;
    public static long skyTargetHashA;
    public static long skyTargetHashB;
    private TeleportFlashProbe() {}
    public static void armOnPromote(Object... args) {}
    public static void armManual(Object... args) {}
    public static void onFrameEnd(Object... args) {}
}
""")

write_stub("common/src/main/java/qouteall/imm_ptl/core/compat/iris_compatibility/ShaderpackViewsProbe.java", """package qouteall.imm_ptl.core.compat.iris_compatibility;
public final class ShaderpackViewsProbe {
    private ShaderpackViewsProbe() {}
    public static void onPostLevelAnchor(Object... args) {}
}
""")

write_stub("common/src/main/java/com/warwa/seamlessportals/render/SeamHandStageDiff.java", """package com.warwa.seamlessportals.render;
public final class SeamHandStageDiff {
    private SeamHandStageDiff() {}
    public static void stageA(Object... args) {}
    public static void stageB(Object... args) {}
    public static void stageC(Object... args) {}
    public static void stageD(Object... args) {}
}
""")

write_stub("common/src/main/java/com/warwa/seamlessportals/render/SeamDestContentProbe.java", """package com.warwa.seamlessportals.render;
public final class SeamDestContentProbe {
    private SeamDestContentProbe() {}
    public static void sample(Object... args) {}
}
""")

write_stub("common/src/main/java/com/warwa/seamlessportals/render/SeamHandLocator.java", """package com.warwa.seamlessportals.render;
public final class SeamHandLocator {
    private SeamHandLocator() {}
    public static void anchor(Object... args) {}
    public static void preSolid(Object... args) {}
    public static void postSolid(Object... args) {}
    public static void postBlit(Object... args) {}
}
""")

write_stub("common/src/main/java/com/warwa/seamlessportals/render/SeamHandSubmitTap.java", """package com.warwa.seamlessportals.render;
public final class SeamHandSubmitTap {
    private SeamHandSubmitTap() {}
    public static void beginSolid(Object... args) {}
    public static void endSolid(Object... args) {}
    public static void beginTranslucent(Object... args) {}
    public static void endTranslucent(Object... args) {}
    public static void onCanRender(Object... args) {}
    public static void onBodyEntered(Object... args) {}
}
""")

write_stub("common/src/main/java/com/warwa/seamlessportals/render/SeamHandInLevelProbe.java", """package com.warwa.seamlessportals.render;
public final class SeamHandInLevelProbe {
    private SeamHandInLevelProbe() {}
    public static void anchor(Object... args) {}
    public static void preSolid(Object... args) {}
    public static void postSolid(Object... args) {}
    public static void preTranslucent(Object... args) {}
    public static void postTranslucent(Object... args) {}
}
""")



# --- 26.3 exact API reconciliation, pass 2 ---

# ServerboundUseItemOnPacket became a record; use record accessors and the renamed swing source.
p = root / "common/src/main/java/qouteall/imm_ptl/core/block_manipulation/BlockManipulationServer.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace("packet.getHitResult()", "packet.hitResult()")
    t = t.replace("packet.getSequence()", "packet.sequence()")
    t = t.replace("packet.getHand()", "packet.hand()")
    t = t.replace("InteractionResult.SwingSource.SERVER", "InteractionResult.SwingSource.SERVER_ONLY")
    t = t.replace(
        "player.swing(hand, true);",
        "player.swing(hand, net.minecraft.world.entity.SwingAnimation.DEFAULT, true);"
    )
    p.write_text(t, encoding="utf-8")

# 26.3 environment colors are already Vector3fc values; do not convert them from packed RGB.
for rel in [
    "common/src/main/java/qouteall/imm_ptl/core/render/context_management/DimensionRenderHelper.java",
    "common/src/main/java/com/warwa/seamlessportals/render/DimensionRenderHelper.java",
]:
    p = root / rel
    if p.exists():
        t = p.read_text(encoding="utf-8")
        t = re.sub(
            r"ARGB\.vector3fFromRGB24\(\s*(virtualCamera\.attributeProbe\(\)\.getValue\(\s*EnvironmentAttributes\.(?:BLOCK_LIGHT_TINT|SKY_LIGHT_COLOR|AMBIENT_LIGHT_COLOR|NIGHT_VISION_COLOR),\s*partialTicks\))\s*\)",
            r"\1",
            t,
            flags=re.S
        )
        p.write_text(t, encoding="utf-8")

# Entity invulnerability timer is private in 26.3 but has public accessors.
for rel in [
    "common/src/main/java/qouteall/imm_ptl/core/teleportation/ServerTeleportationManager.java",
    "common/src/main/java/com/warwa/seamlessportals/entity/PortalTeleporter.java",
]:
    p = root / rel
    if p.exists():
        t = p.read_text(encoding="utf-8")
        t = re.sub(
            r"(\b\w+)\.invulnerableTime\s*=\s*(\b\w+)\.invulnerableTime\s*;",
            r"\1.setInvulnerableTime(\2.getInvulnerableTime());",
            t
        )
        p.write_text(t, encoding="utf-8")

# TextureTarget constructor now takes explicit nullable color/depth formats.
p = root / "common/src/main/java/qouteall/imm_ptl/core/render/SecondaryFrameBuffer.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        'width, height,\n                true,//has depth attachment\n                GpuFormat.RGBA8_UNORM',
        'width, height,\n                GpuFormat.RGBA8_UNORM,\n                GpuFormat.D32_FLOAT'
    )
    p.write_text(t, encoding="utf-8")

# Link opening moved to Blaze3D and ConfirmLinkScreen now takes URI directly.
p = root / "common/src/main/java/qouteall/imm_ptl/core/CHelper.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "import com.mojang.blaze3d.Blaze3D;" not in t:
        t = t.replace("package qouteall.imm_ptl.core;\n", "package qouteall.imm_ptl.core;\n\nimport com.mojang.blaze3d.Blaze3D;\n")
    t = t.replace("Util.getPlatform().openUri(new URI(link));", "Blaze3D.openUri(new URI(link));")
    t = t.replace("            link, true\n", "            URI.create(link), true\n")
    p.write_text(t, encoding="utf-8")

# CommandSourceStack's entity-aware constructor no longer accepts explicit name/display-name.
p = root / "common/src/main/java/qouteall/imm_ptl/core/McHelper.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        """            PermissionSet.NO_PERMISSIONS,
            commandSender.getName().getString(),
            commandSender.getDisplayName(),
            ((ServerLevel) commandSender.level()).getServer(),
            commandSender""",
        """            PermissionSet.NO_PERMISSIONS,
            ((ServerLevel) commandSender.level()).getServer(),
            commandSender"""
    )
    p.write_text(t, encoding="utf-8")

# Record accessors for 26.3 clientbound packets.
p = root / "common/src/main/java/qouteall/imm_ptl/core/mixin/client/sync/MixinClientPacketListener.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace("packet.getEntityIds()", "packet.entityIds()")
    t = t.replace("packet.getX()", "packet.x()")
    t = t.replace("packet.getZ()", "packet.z()")
    p.write_text(t, encoding="utf-8")

p = root / "common/src/main/java/com/warwa/seamlessportals/chunk/RedirectedPacketApplier.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace("p.innerPacket().getX()", "p.innerPacket().x()")
    t = t.replace("p.innerPacket().getZ()", "p.innerPacket().z()")
    p.write_text(t, encoding="utf-8")

# InterpolationHandler now uses PositionPath and exposes target() instead of position/yRot/xRot.
p = root / "common/src/main/java/com/warwa/seamlessportals/passthrough/SeamVisualCarryover.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        "(interp != null && interp.hasActiveInterpolation()) ? interp.position() : null",
        "(interp != null && interp.hasActiveInterpolation() && interp.target() != null) ? interp.target().position() : null"
    )
    t = t.replace(
        "interp.interpolateTo(serverPos, fresh.getYRot(), fresh.getXRot());",
        "interp.interpolateTo(net.minecraft.world.entity.PositionPath.of(serverPos), fresh.getYRot(), fresh.getXRot(), true);"
    )
    p.write_text(t, encoding="utf-8")

p = root / "common/src/main/java/com/warwa/seamlessportals/chunk/RemoteEntityApplier.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        """interp.interpolateTo(
                new net.minecraft.world.phys.Vec3(p.x(), p.y(), p.z()),
                p.yRot(), p.xRot());""",
        """interp.interpolateTo(
                net.minecraft.world.entity.PositionPath.of(new net.minecraft.world.phys.Vec3(p.x(), p.y(), p.z())),
                p.yRot(), p.xRot(), true);"""
    )
    p.write_text(t, encoding="utf-8")

p = root / "common/src/main/java/qouteall/imm_ptl/core/teleportation/ClientTeleportationManager.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        """if (interp != null && interp.hasActiveInterpolation()) {
                interp.interpolateTo(
                    p.transformPoint(interp.position()), interp.yRot(), interp.xRot());
            }""",
        """if (interp != null && interp.hasActiveInterpolation() && interp.target() != null) {
                var target = interp.target();
                interp.interpolateTo(
                    net.minecraft.world.entity.PositionPath.of(p.transformPoint(target.position())),
                    target.yRot(), target.xRot(), true);
            }"""
    )
    p.write_text(t, encoding="utf-8")

# PoseStack's quaternion operation is rotate(Quaternionfc) in 26.3.
p = root / "common/src/main/java/qouteall/imm_ptl/core/mc_utils/WireRenderingHelper.java"
if p.exists():
    t = p.read_text(encoding="utf-8").replace("matrixStack.mulPose(", "matrixStack.rotate(")
    p.write_text(t, encoding="utf-8")

# RenderTarget.useDepth is gone; depth attachment presence is authoritative.
p = root / "common/src/main/java/qouteall/imm_ptl/core/render/GuiPortalRendering.java"
if p.exists():
    t = p.read_text(encoding="utf-8").replace(
        "if (framebuffer.useDepth) {",
        "if (framebuffer.getDepthTexture() != null) {"
    )
    p.write_text(t, encoding="utf-8")

# The old Iris bloom aperture implementation reaches RenderPearl's package-private GL backend.
# Keep its public hook surface but disable only this shader-pack-specific bloom workaround on 26.3.
write_stub("common/src/main/java/qouteall/imm_ptl/core/compat/iris_compatibility/IrisBloomApertureMask.java", """package qouteall.imm_ptl.core.compat.iris_compatibility;
import net.irisshaders.iris.pipeline.CompositeRenderer;
import org.joml.Matrix4f;
import net.minecraft.world.phys.Vec3;
import qouteall.imm_ptl.core.portal.Portal;
public final class IrisBloomApertureMask {
    private IrisBloomApertureMask() {}
    public static void arm(Portal portal, Matrix4f modelView, Matrix4f projection, Vec3 cameraPos, float partialTick) {}
    public static void disarmAndReport() {}
    public static void onCompositePassBoundary(CompositeRenderer renderer, int i) {}
    public static void teardown() {}
}
""")

# Sodium's private destination-chunk arm hook changed again in 0.9.2. Core rendering has a
# vanilla fallback path, so disable this optimization until the runtime pass is green.
p = root / "common/src/main/java/qouteall/imm_ptl/core/compat/sodium_compatibility/SodiumInterface.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    marker2 = "        public boolean ip_armDestChunkRenders("
    if marker2 in t:
        a = t.index(marker2)
        brace = t.index("{", a)
        depth = 0
        end = None
        for i in range(brace, len(t)):
            if t[i] == "{": depth += 1
            elif t[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        header = t[a:brace+1]
        t = t[:a] + header + "\n            return false;\n        }" + t[end:]
    p.write_text(t, encoding="utf-8")

# 26.3 chunk packets expose record accessors and ClientChunkCache accepts the packet-data object.
# Update our two custom cache subclasses to the new override and keep old raw-buffer overloads inert.
for rel in [
    "common/src/main/java/qouteall/imm_ptl/core/chunk_loading/ImmPtlClientChunkMap.java",
    "common/src/main/java/com/warwa/seamlessportals/client/SeamlessClientChunkMap.java",
]:
    p = root / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    # Remove @Override only from the old raw-buffer overload.
    t = t.replace(
        """    @Override
    public @Nullable LevelChunk replaceWithPacketData(
        int x, int z,
        FriendlyByteBuf buf, Map<Heightmap.Types, long[]> heightmaps,""",
        """    public @Nullable LevelChunk replaceWithPacketData(
        int x, int z,
        FriendlyByteBuf buf, Map<Heightmap.Types, long[]> heightmaps,"""
    )
    t = t.replace(
        """    @Override
    public @Nullable LevelChunk replaceWithPacketData(
            int chunkX, int chunkZ, FriendlyByteBuf readBuffer,""",
        """    public @Nullable LevelChunk replaceWithPacketData(
            int chunkX, int chunkZ, FriendlyByteBuf readBuffer,"""
    )
    # Old LevelChunk raw-buffer decode API disappeared. Leave overload for source compatibility only.
    t = re.sub(
        r"worldChunk\.replaceWithPacketData\(buf, heightmaps, consumer\);",
        r'throw new UnsupportedOperationException("26.3 raw chunk decode removed");',
        t
    )
    t = re.sub(
        r"chunk\.replaceWithPacketData\(readBuffer, heightmaps, blockEntities\);",
        r'throw new UnsupportedOperationException("26.3 raw chunk decode removed");',
        t
    )
    p.write_text(t, encoding="utf-8")

# Add real 26.3 packet-data overrides to the custom caches.
p = root / "common/src/main/java/com/warwa/seamlessportals/client/SeamlessClientChunkMap.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    anchor = "    @Override\n    public void replaceBiomes("
    if anchor in t and "ClientboundLevelChunkPacketData chunkData)" not in t:
        method = """    @Override
    public @Nullable LevelChunk replaceWithPacketData(
            int chunkX, int chunkZ, ClientboundLevelChunkPacketData chunkData) {
        long key = ChunkPos.pack(chunkX, chunkZ);
        ChunkPos pos = new ChunkPos(chunkX, chunkZ);
        LevelChunk chunk = readMap(m -> m.get(key));
        if (chunk == null) {
            chunk = new LevelChunk(this.ccLevel, pos);
            final LevelChunk added = chunk;
            modifyMap(m -> m.put(key, added));
            emitChunkAdded(chunk);
        }
        chunk.replaceWithPacketData(chunkX, chunkZ, chunkData);
        emitRefresh(chunk);
        this.ccLevel.onChunkLoaded(pos);
        return chunk;
    }

"""
        t = t.replace(anchor, method + anchor)
    p.write_text(t, encoding="utf-8")

p = root / "common/src/main/java/qouteall/imm_ptl/core/chunk_loading/ImmPtlClientChunkMap.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    anchor = "    /**\n     * {@link net.minecraft.core.IdMap#byIdOrThrow(int)}"
    if anchor in t and "ClientboundLevelChunkPacketData chunkData)" not in t:
        method = """    @Override
    public @Nullable LevelChunk replaceWithPacketData(
        int x, int z, ClientboundLevelChunkPacketData chunkData
    ) {
        Validate.isTrue(Thread.currentThread() == mainThread);
        long key = ChunkPos.pack(x, z);
        LevelChunk chunk = chunkMapForMainThread.get(key);
        if (chunk == null) {
            chunk = new LevelChunk(this.level, new ChunkPos(x, z));
            final LevelChunk added = chunk;
            modifyChunkMap(m -> m.put(key, added));
            emitChunkAdded(chunk);
        }
        chunk.replaceWithPacketData(x, z, chunkData);
        emitRefresh(chunk);
        this.level.onChunkLoaded(new ChunkPos(x, z));
        O_O.postClientChunkLoadEvent(chunk);
        SodiumInterface.invoker.onClientChunkLoaded(level, x, z);
        clientChunkLoadSignal.emit(chunk);
        return chunk;
    }

"""
        t = t.replace(anchor, method + anchor)
    p.write_text(t, encoding="utf-8")

# Remove the stale chunk-decode guard mixin; 26.3's packet-data object validates decoding itself.
for mixfile in (root / "common/src/main/resources").glob("*.mixins.json"):
    try:
        data = json.loads(mixfile.read_text(encoding="utf-8"))
    except Exception:
        continue
    changed = False
    for key in ("mixins", "client"):
        arr = data.get(key)
        if isinstance(arr, list):
            filtered = [x for x in arr if "ChunkPacketGuardMixin" not in x]
            if filtered != arr:
                data[key] = filtered
                changed = True
    if changed:
        mixfile.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
# Remove its source too so obsolete redirect signatures cannot block compilation.
p = root / "common/src/main/java/com/warwa/seamlessportals/mixin/client/ChunkPacketGuardMixin.java"
if p.exists():
    p.unlink()


# --- 26.3 exact API reconciliation, pass 3 ---

# Player-action packet stayed a class in 26.3; keep getSequence(). SwingAnimation moved to item components.
p = root / "common/src/main/java/qouteall/imm_ptl/core/block_manipulation/BlockManipulationServer.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    # Only ServerboundPlayerActionPacket sites should use getSequence; use-item packet remains sequence().
    t = t.replace("world.getMaxY(), packet.sequence()", "world.getMaxY(), packet.getSequence()")
    t = t.replace("ackBlockChangesUpTo(packet.sequence())", "ackBlockChangesUpTo(packet.getSequence())")
    t = t.replace(
        "net.minecraft.world.entity.SwingAnimation.DEFAULT",
        "net.minecraft.world.item.component.SwingAnimation.DEFAULT"
    )
    p.write_text(t, encoding="utf-8")

# Patch every Sodium destination-arm implementation, not only the first anonymous implementation.
p = root / "common/src/main/java/qouteall/imm_ptl/core/compat/sodium_compatibility/SodiumInterface.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    marker3 = "        public boolean ip_armDestChunkRenders("
    search_from = 0
    while True:
        a = t.find(marker3, search_from)
        if a < 0:
            break
        brace = t.find("{", a)
        depth = 0
        end = None
        for i in range(brace, len(t)):
            if t[i] == "{":
                depth += 1
            elif t[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise SystemExit("Could not close ip_armDestChunkRenders")
        header = t[a:brace + 1]
        replacement = header + "\n            return false;\n        }"
        t = t[:a] + replacement + t[end:]
        search_from = a + len(replacement)
    p.write_text(t, encoding="utf-8")

# 26.3 createPlayer carries ItemActivation through respawns. Update both redirect descriptors and calls.
p = root / "common/src/main/java/com/warwa/seamlessportals/mixin/client/HandleRespawnMixin.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        '"Lnet/minecraft/world/entity/player/Input;Z)"',
        '"Lnet/minecraft/world/entity/player/Input;Z"\n'
        '                + "Lnet/minecraft/client/player/ItemActivation;)"'
    )
    # The previous string assembly can vary; normalize the exact descriptor fragment if it remained.
    t = t.replace(
        '+ "Lnet/minecraft/world/entity/player/Input;Z)"\n                + "Lnet/minecraft/client/player/LocalPlayer;"',
        '+ "Lnet/minecraft/world/entity/player/Input;Z"\n'
        '                + "Lnet/minecraft/client/player/ItemActivation;)"\n'
        '                + "Lnet/minecraft/client/player/LocalPlayer;"'
    )
    t = t.replace(
        """            Input lastSentInput,
            boolean wasSprinting) {""",
        """            Input lastSentInput,
            boolean wasSprinting,
            net.minecraft.client.player.ItemActivation itemActivation) {"""
    )
    t = t.replace(
        "return gameMode.createPlayer(level, stats, recipeBook, lastSentInput, wasSprinting);",
        "return gameMode.createPlayer(level, stats, recipeBook, lastSentInput, wasSprinting, itemActivation);"
    )
    t = t.replace(
        '+ "Lnet/minecraft/client/ClientRecipeBook;)"',
        '+ "Lnet/minecraft/client/ClientRecipeBook;"\n'
        '                + "Lnet/minecraft/client/player/ItemActivation;)"'
    )
    t = t.replace(
        """            StatsCounter stats,
            ClientRecipeBook recipeBook) {""",
        """            StatsCounter stats,
            ClientRecipeBook recipeBook,
            net.minecraft.client.player.ItemActivation itemActivation) {"""
    )
    t = t.replace(
        "return gameMode.createPlayer(level, stats, recipeBook);",
        "return gameMode.createPlayer(level, stats, recipeBook, itemActivation);"
    )
    p.write_text(t, encoding="utf-8")

# Raw section-buffer prefeed was removed from ClientChunkCache. Those sites are only warm-up paths;
# let the redirected vanilla ClientboundLevelChunk packet populate the destination cache instead.
for rel in [
    "common/src/main/java/com/warwa/seamlessportals/client/PortalWorldManager.java",
    "common/src/main/java/com/warwa/seamlessportals/client/PortalDimensionManager.java",
    "common/src/main/java/com/warwa/seamlessportals/mixin/client/HandleRespawnMixin.java",
]:
    p = root / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    t = re.sub(
        r"cache\.replaceWithPacketData\(\s*chunkX,\s*chunkZ,\s*(?:buf|chunkPacket),\s*java\.util\.Collections\.emptyMap\(\),\s*tag\s*->\s*\{\}\s*\);",
        "/* 26.3: raw chunk prefeed removed; redirected vanilla packet owns cache population. */",
        t,
        flags=re.S
    )
    t = re.sub(
        r"cache\.replaceWithPacketData\(\s*pos\.x\(\),\s*pos\.z\(\),\s*buf,\s*java\.util\.Collections\.emptyMap\(\),\s*tag\s*->\s*\{\}\s*\);",
        "/* 26.3: raw chunk prefeed removed; server packet will refill this chunk. */",
        t,
        flags=re.S
    )
    p.write_text(t, encoding="utf-8")

# PreparedRenderType now consumes a StagedVertexBuffer.ExecuteInfo plus an explicit RenderPass.
p = root / "common/src/main/java/com/warwa/seamlessportals/render/PortalRenderTypes.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    old = """                renderType.prepare().drawFromBuffer(
                    vertexBuffer, indexBuffer, indexType, 0, 0, indexCount);"""
    new = """                var info = new net.minecraft.client.renderer.StagedVertexBuffer.ExecuteInfo(
                    vertexBuffer, indexBuffer, indexType, 0, 0, indexCount,
                    drawState.primitiveTopology()
                );
                var target = net.minecraft.client.Minecraft.getInstance().gameRenderer.mainRenderTarget();
                var descriptorBuilder = com.mojang.renderpearl.api.commands.RenderPassDescriptor
                    .builder(() -> "seamlessportals immediate mesh")
                    .withColorAttachment(java.util.Objects.requireNonNull(target.getColorTextureView()));
                if (target.getDepthTextureView() != null) {
                    descriptorBuilder.withDepthAttachment(target.getDepthTextureView());
                }
                try (var pass = RenderSystem.getDevice().createCommandEncoder()
                    .createRenderPass(descriptorBuilder.build())) {
                    renderType.prepare().drawFromBuffer(info, pass);
                }"""
    if old in t:
        t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")


# --- 26.3 renderer convergence: keep full LevelRenderer/FBO path, retire removed manual subpasses ---

def port263_replace_method(src, marker_text, body_text):
    start = src.find(marker_text)
    if start < 0:
        return src
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit(f"Missing brace for {marker_text}")
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
        raise SystemExit(f"Unclosed method {marker_text}")
    header = src[start:brace + 1]
    return src[:start] + header + "\n" + body_text + "\n    }" + src[end:]

# Correct the one use-item ack that the class-vs-record split left behind.
p = root / "common/src/main/java/qouteall/imm_ptl/core/block_manipulation/BlockManipulationServer.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    # ServerboundUseItemOnPacket is a record in 26.3.
    t = t.replace("ackBlockChangesUpTo(packet.getSequence())", "ackBlockChangesUpTo(packet.sequence())")
    # The destroy-action packet is still a normal class.
    t = t.replace("world.getMaxY(), packet.sequence()", "world.getMaxY(), packet.getSequence()")
    p.write_text(t, encoding="utf-8")

# SecondaryWorldRenderCore: the selected 26.3 route is renderDestWorldFullPipeline.
# Update that route to current signatures; old decomposed helper subpasses are now dead.
p = root / "common/src/main/java/qouteall/imm_ptl/core/render/SecondaryWorldRenderCore.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        "newCamera.extractRenderState(destCameraState, partialTick);",
        "newCamera.extractRenderState(destCameraState, deltaTracker);"
    )
    t = t.replace("destLevel.getGameTime(), deltaTracker,", "destLevel.getGameTime(), partialTick,")
    t = t.replace("savedLevelGameTime, deltaTracker,", "savedLevelGameTime, partialTick,")

    old_render = """destRenderer.render(
                GraphicsResourceAllocator.UNPOOLED,
                deltaTracker,
                renderOutline,
                destCameraState,
                destDrawViewMatrix,
                destFogBuffer,
                destFogData.color,
                true
            );"""
    new_render = """destRenderer.render(
                GraphicsResourceAllocator.UNPOOLED,
                renderOutline,
                destCameraState,
                destFogBuffer,
                destFogData.color,
                true,
                false
            );"""
    t = t.replace(old_render, new_render)

    # A second formatting variant exists in the inherited full-pipeline source.
    t = re.sub(
        r"destRenderer\.render\(\s*GraphicsResourceAllocator\.UNPOOLED,\s*deltaTracker,\s*"
        r"(?:renderOutline|false),\s*destCameraState,\s*(?:destDrawViewMatrix|destViewMatrix),\s*"
        r"destFogBuffer,\s*destFogData\.color,\s*true\s*\);",
        """destRenderer.render(
                GraphicsResourceAllocator.UNPOOLED,
                false,
                destCameraState,
                destFogBuffer,
                destFogData.color,
                true,
                false
            );""",
        t,
        flags=re.S
    )

    # These methods implement the removed 26.2 decomposed/manual renderer. The full renderer
    # above now owns sky/cloud/weather/entity passes on 26.3.
    for meth in [
        "    private static void renderPortalSky(",
        "    private static void renderPortalClouds(",
        "    private static void renderPortalWeather(",
        "    private static void renderPortalEntities(",
        "    private static void renderPortalEntitiesSameDim(",
    ]:
        t = port263_replace_method(t, meth, "        // 26.3: handled by the full LevelRenderer pipeline.")
    p.write_text(t, encoding="utf-8")

# Per-entity deferred feature replay depended on the 26.2 SubmitNodeStorage execution API.
# Keep collection/clip state intact but disable the old replay primitive for the first 26.3 build.
p = root / "common/src/main/java/qouteall/imm_ptl/core/render/PerEntityClipBracket.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = port263_replace_method(
        t,
        "    public static void drawBracketedEntitiesIfAny(",
        "        // 26.3: entity features are executed by the full FeatureRenderDispatcher frame."
    )
    t = port263_replace_method(
        t,
        "    public static boolean drawImmediateClipped(",
        "        // 26.3: legacy immediate feature replay disabled; full renderer owns execution.\n        return false;"
    )
    p.write_text(t, encoding="utf-8")

# PortalContextSwitch's FBO path remains useful on 26.3. Its stencil-direct mode, however,
# depended on private ChunkSectionsToRender internals removed in 26.3. Disable only direct mode.
p = root / "common/src/main/java/com/warwa/seamlessportals/render/PortalContextSwitch.java"
if p.exists():
    t = p.read_text(encoding="utf-8")

    t = port263_replace_method(
        t,
        "    public static boolean renderDestinationDirect(",
        "        // 26.3: use the FBO/full-LevelRenderer route; direct chunk subpasses were removed upstream.\n        return false;"
    )

    # Direct-only helper methods are no longer reachable.
    for meth in [
        "    private static void renderPortalSky(",
        "    private static void renderPortalClouds(",
        "    private static void renderPortalEntities(",
    ]:
        t = port263_replace_method(t, meth, "        // 26.3: handled by LevelRenderer.render().")

    t = t.replace(
        "virtualCamera.extractRenderState(destCameraState, partialTick);",
        "virtualCamera.extractRenderState(destCameraState, deltaTracker);"
    )
    t = t.replace("destLevel.getGameTime(), deltaTracker,", "destLevel.getGameTime(), partialTick,")
    t = t.replace("savedLevelGameTime, deltaTracker,", "savedLevelGameTime, partialTick,")

    # The precomputed ChunkSectionsToRender block existed only for the removed direct path and
    # debug counters. FBO mode lets LevelRenderer prepare/compile/upload its own terrain.
    start_marker = "                    // 26.2: ChunkSectionsToRender is produced by"
    end_marker = "                    // Inner clip plane"
    if start_marker in t:
        a = t.index(start_marker)
        b = t.index(end_marker, a)
        t = t[:a] + """                    // 26.3: LevelRenderer owns chunk preparation and uploads.
                    GL11.glDisable(GL11.GL_STENCIL_TEST);
""" + t[b:]

    # This explicit Sodium re-point targeted the precomputed direct-path chunk object and was
    # already documented as redundant under the renderer's own Sodium wrap.
    t = re.sub(
        r"\s*com\.warwa\.seamlessportals\.compat\.SodiumBridge\s*"
        r"\.updateChunkSectionsRenderer\(\s*destChunks,\s*destRenderer,\s*"
        r"destCameraState\.projectionMatrix,\s*destViewMatrix,\s*"
        r"destCameraPos\.x,\s*destCameraPos\.y,\s*destCameraPos\.z\);",
        "",
        t,
        flags=re.S
    )

    # Replace the remaining direct-vs-FBO draw fork with the native 26.3 full render.
    direct_comment = "// Phase 5 STEP 1: draw the dest terrain DIRECTLY"
    if direct_comment in t:
        comment_pos = t.index(direct_comment)
        if_pos = t.rfind("if (stencilDirectMode) {", 0, comment_pos)
        finally_marker = "\n                            } finally {\n                                com.warwa.seamlessportals.render.SodiumFogOverride.clear();"
        fin = t.index(finally_marker, comment_pos)
        replacement = """destRenderer.render(
                                    GraphicsResourceAllocator.UNPOOLED,
                                    false,
                                    destCameraState,
                                    destFogBuffer,
                                    destFogData.color,
                                    true,
                                    false
                                );"""
        t = t[:if_pos] + replacement + t[fin:]

    # Any inherited old-signature FBO render that remains gets the same 26.3 signature.
    t = re.sub(
        r"destRenderer\.render\(\s*GraphicsResourceAllocator\.UNPOOLED,\s*deltaTracker,\s*false,\s*"
        r"destCameraState,\s*destViewMatrix,\s*destFogBuffer,\s*destFogData\.color,\s*true\s*\);",
        """destRenderer.render(
                                    GraphicsResourceAllocator.UNPOOLED,
                                    false,
                                    destCameraState,
                                    destFogBuffer,
                                    destFogData.color,
                                    true,
                                    false
                                );""",
        t,
        flags=re.S
    )
    p.write_text(t, encoding="utf-8")


# --- 26.3 final compile-signature pass ---

p = root / "common/src/main/java/qouteall/imm_ptl/core/block_manipulation/BlockManipulationServer.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    use_marker = "private static void doProcessUseItemOn("
    if use_marker in t:
        a = t.index(use_marker)
        b = t.index("    public static void", a) if "    public static void" in t[a:] else len(t)
        before, segment, after = t[:a], t[a:b], t[b:]
        segment = segment.replace("ackBlockChangesUpTo(packet.getSequence())", "ackBlockChangesUpTo(packet.sequence())")
        t = before + segment + after
    # Player-action packet remains getter-based.
    action_marker = "private static void doProcessPlayerAction("
    if action_marker in t:
        a = t.index(action_marker)
        b = t.index("    public static boolean isAttackingAction", a)
        seg = t[a:b].replace("packet.sequence()", "packet.getSequence()")
        t = t[:a] + seg + t[b:]
    p.write_text(t, encoding="utf-8")

p = root / "common/src/main/java/qouteall/imm_ptl/core/render/SecondaryWorldRenderCore.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"(destLevel\.getGameTime\(\),\s*)deltaTracker,", r"\1partialTick,", t)
    t = re.sub(r"(savedLevelGameTime,\s*)deltaTracker,", r"\1partialTick,", t)
    t = t.replace(
        """destRenderer.render(
                GraphicsResourceAllocator.UNPOOLED,
                deltaTracker,
                destRenderOutline,
                destCameraState,
                destDrawViewMatrix,
                destFogBuffer,
                destFogData.color,
                WorldRenderInfo.getTopRenderInfo().doRenderSky
            );""",
        """destRenderer.render(
                GraphicsResourceAllocator.UNPOOLED,
                destRenderOutline,
                destCameraState,
                destFogBuffer,
                destFogData.color,
                WorldRenderInfo.getTopRenderInfo().doRenderSky,
                false
            );"""
    )
    p.write_text(t, encoding="utf-8")

p = root / "common/src/main/java/com/warwa/seamlessportals/render/PortalContextSwitch.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = re.sub(r"(destLevel\.getGameTime\(\),\s*)deltaTracker,", r"\1partialTick,", t)
    t = re.sub(r"(savedLevelGameTime,\s*)deltaTracker,", r"\1partialTick,", t)
    p.write_text(t, encoding="utf-8")


# --- 26.3 catch the commented full-pipeline render call ---
p = root / "common/src/main/java/qouteall/imm_ptl/core/render/SecondaryWorldRenderCore.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = re.sub(
        r"destRenderer\.render\(\s*GraphicsResourceAllocator\.UNPOOLED,\s*deltaTracker,\s*"
        r"(destRenderOutline|renderOutline|false),\s*destCameraState,\s*"
        r"(?:/\*.*?\*/\s*|//[^\n]*\n\s*)*destDrawViewMatrix,\s*"
        r"destFogBuffer,\s*destFogData\.color,\s*"
        r"(WorldRenderInfo\.getTopRenderInfo\(\)\.doRenderSky|true)\s*\);",
        lambda m: """destRenderer.render(
                GraphicsResourceAllocator.UNPOOLED,
                %s,
                destCameraState,
                destFogBuffer,
                destFogData.color,
                %s,
                false
            );""" % (m.group(1), m.group(2)),
        t,
        flags=re.S
    )
    # Hard assertion: no 26.2 render signature may survive this port script.
    if re.search(r"destRenderer\.render\(\s*GraphicsResourceAllocator\.UNPOOLED,\s*deltaTracker,", t, flags=re.S):
        raise SystemExit("A 26.2 LevelRenderer.render signature survived the 26.3 port")
    p.write_text(t, encoding="utf-8")


# --- 26.3 retire legacy raw-buffer chunk overloads cleanly ---
for rel in [
    "common/src/main/java/com/warwa/seamlessportals/client/SeamlessClientChunkMap.java",
    "common/src/main/java/qouteall/imm_ptl/core/chunk_loading/ImmPtlClientChunkMap.java",
]:
    p = root / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    t = port263_replace_method(
        t,
        "    public @Nullable LevelChunk replaceWithPacketData(\n",
        "        // 26.3 removed raw FriendlyByteBuf chunk decode; packet-data overload is authoritative.\n        return null;"
    )
    p.write_text(t, encoding="utf-8")

print("Applied Minecraft 26.3 baseline patch")
