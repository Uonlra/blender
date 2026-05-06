import math
import os
import random
import sys

import bpy
from mathutils import Vector


FRAME_START = 1
FRAME_END = 120
FPS = 24
DONUT_MAJOR_RADIUS = 1.18
DONUT_MINOR_RADIUS = 0.38


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def set_origin_center(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.select_set(False)


def make_mat(name, color, metallic=0.0, roughness=0.45, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if emission and emission_input:
            emission_input.default_value = emission
        strength_input = bsdf.inputs.get("Emission Strength")
        if strength_input:
            strength_input.default_value = strength
    return mat


def parent_to(obj, parent):
    obj.parent = parent
    return obj


def donut_upper_z(radius):
    offset = radius - DONUT_MAJOR_RADIUS
    return math.sqrt(max(0.0, DONUT_MINOR_RADIUS * DONUT_MINOR_RADIUS - offset * offset))


def icing_edge_profiles(angle):
    outer_wave = (
        0.045 * math.sin(7 * angle + 0.4)
        + 0.027 * math.sin(13 * angle + 1.7)
        + 0.018 * math.sin(23 * angle)
    )
    inner_wave = 0.024 * math.sin(8 * angle + 2.1) + 0.012 * math.sin(19 * angle)
    return 0.84 + inner_wave, 1.50 + outer_wave


def icing_surface_z(radius, angle, radial_t):
    crown = math.sin(math.pi * radial_t)
    ripple = 0.018 * math.sin(5 * angle + radial_t * 2.4) + 0.011 * math.sin(17 * angle)
    edge_falloff = 0.055 * (abs(radial_t - 0.5) * 2.0) ** 1.4
    return donut_upper_z(radius) + 0.052 + 0.045 * crown + ripple - edge_falloff


def add_bread_torus(mat):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=192,
        minor_segments=36,
        major_radius=DONUT_MAJOR_RADIUS,
        minor_radius=DONUT_MINOR_RADIUS,
        location=(0, 0, 0),
    )
    obj = bpy.context.object
    obj.name = "golden_donut_body"
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    obj.modifiers.new(name="soft_bakery_normals", type="WEIGHTED_NORMAL")
    return obj


def add_icing_mesh(mat):
    random.seed(23)
    segments = 192
    rings = 14
    verts = []
    faces = []
    outer_profile = []
    inner_profile = []

    for i in range(segments):
        u = (i / segments) * math.tau
        inner_radius, outer_radius = icing_edge_profiles(u)
        outer_profile.append(outer_radius)
        inner_profile.append(inner_radius)

    for i in range(segments):
        u = (i / segments) * math.tau
        cu, su = math.cos(u), math.sin(u)
        for j in range(rings):
            t = j / (rings - 1)
            radius = inner_profile[i] * (1 - t) + outer_profile[i] * t
            z = icing_surface_z(radius, u, t)
            verts.append((radius * cu, radius * su, z))

    for i in range(segments):
        ni = (i + 1) % segments
        for j in range(rings - 1):
            faces.append(
                (
                    i * rings + j,
                    ni * rings + j,
                    ni * rings + j + 1,
                    i * rings + j + 1,
                )
            )

    mesh = bpy.data.meshes.new("pink_icing_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("wavy_pink_icing", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.modifiers.new(name="soft_icing", type="SUBSURF").levels = 1
    obj.modifiers.new(name="glossy_normals", type="WEIGHTED_NORMAL")
    obj.select_set(False)
    return obj


def add_icing_drips(mat):
    drips = []
    for idx, angle in enumerate([0.1, 0.55, 1.15, 1.8, 2.45, 3.05, 3.75, 4.35, 5.0, 5.65]):
        _, outer_radius = icing_edge_profiles(angle)
        radius = outer_radius - 0.015
        length = 0.16 + 0.08 * ((idx % 3) / 2)
        width = 0.08 + 0.025 * (idx % 2)
        x, y = radius * math.cos(angle), radius * math.sin(angle)
        edge_z = icing_surface_z(radius, angle, 1.0)
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=24,
            ring_count=12,
            radius=1,
            location=(x, y, edge_z - length * 0.42),
        )
        drip = bpy.context.object
        drip.name = f"rounded_icing_drip_{idx + 1}"
        drip.scale = (width, width * 0.55, length)
        drip.rotation_euler[2] = angle
        drip.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        drips.append(drip)
    return drips


def add_sprinkles(materials):
    random.seed(7)
    sprinkles = []
    for i in range(90):
        angle = random.random() * math.tau
        inner_radius, outer_radius = icing_edge_profiles(angle)
        t = random.uniform(0.18, 0.86)
        radius = inner_radius * (1 - t) + outer_radius * t
        x, y = radius * math.cos(angle), radius * math.sin(angle)
        z = icing_surface_z(radius, angle, t) + random.uniform(0.022, 0.045)
        length = random.uniform(0.10, 0.16)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
        sprinkle = bpy.context.object
        sprinkle.name = f"candy_sprinkle_{i + 1:02d}"
        sprinkle.dimensions = (length, 0.026, 0.026)
        sprinkle.rotation_euler = (
            random.uniform(-0.18, 0.18),
            random.uniform(-0.18, 0.18),
            angle + random.uniform(-math.pi, math.pi),
        )
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        sprinkle.data.materials.append(random.choice(materials))
        sprinkle.modifiers.new(name="tiny_bevel", type="BEVEL").width = 0.012
        sprinkle.modifiers.new(name="smooth_normals", type="WEIGHTED_NORMAL")
        sprinkles.append(sprinkle)
    return sprinkles


def add_bread_texture_dots(parent, mat):
    random.seed(41)
    dots = []
    for i in range(130):
        angle = random.random() * math.tau
        minor = random.uniform(-0.9, 0.65)
        ring_radius = 1.18 + 0.37 * math.cos(minor)
        x, y = ring_radius * math.cos(angle), ring_radius * math.sin(angle)
        z = 0.37 * math.sin(minor)
        if z > 0.24:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=random.uniform(0.012, 0.028), location=(x, y, z))
        dot = bpy.context.object
        dot.name = f"baked_texture_pore_{i + 1:03d}"
        dot.data.materials.append(mat)
        parent_to(dot, parent)
        dots.append(dot)
    return dots


def animate_rig(rig):
    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.frame_set(FRAME_START)

    rig.rotation_euler = (math.radians(62), 0, math.radians(-20))
    rig.keyframe_insert(data_path="rotation_euler", frame=FRAME_START)
    rig.rotation_euler = (math.radians(62), 0, math.radians(340))
    rig.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

    if rig.animation_data and rig.animation_data.action:
        action = rig.animation_data.action
        fcurves = getattr(action, "fcurves", None)
        if fcurves:
            for fcurve in fcurves:
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = "LINEAR"


def add_camera_and_lights():
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    focus = bpy.context.object
    focus.name = "camera_focus"

    bpy.ops.object.camera_add(location=(0, -4.7, 2.05), rotation=(math.radians(67), 0, 0))
    camera = bpy.context.object
    camera.name = "render_camera"
    bpy.context.scene.camera = camera
    camera.data.lens = 58
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = 8.0

    bpy.ops.object.light_add(type="AREA", location=(-2.6, -3.0, 4.0), rotation=(math.radians(62), 0, math.radians(-28)))
    key = bpy.context.object
    key.name = "large_softbox_key"
    key.data.energy = 520
    key.data.size = 5.0

    bpy.ops.object.light_add(type="AREA", location=(2.8, 2.5, 3.4), rotation=(math.radians(50), 0, math.radians(140)))
    rim = bpy.context.object
    rim.name = "soft_rim_light"
    rim.data.energy = 95
    rim.data.size = 4.0

    return focus, camera


def create_scene():
    clear_scene()

    bread = make_mat("warm_golden_bread", (0.93, 0.48, 0.13, 1), roughness=0.42)
    toasted = make_mat("toasted_pores", (0.44, 0.18, 0.055, 1), roughness=0.72)
    icing = make_mat("glossy_strawberry_icing", (1.0, 0.42, 0.58, 1), roughness=0.18)
    sprinkle_mats = [
        make_mat("sprinkle_white", (1.0, 0.97, 0.92, 1), roughness=0.32),
        make_mat("sprinkle_yellow", (1.0, 0.72, 0.12, 1), roughness=0.32),
        make_mat("sprinkle_blue", (0.22, 0.78, 1.0, 1), roughness=0.32),
        make_mat("sprinkle_hot_pink", (1.0, 0.12, 0.42, 1), roughness=0.32),
        make_mat("sprinkle_red", (0.96, 0.08, 0.08, 1), roughness=0.32),
    ]

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "angled_rotating_donut_rig"

    body = parent_to(add_bread_torus(bread), rig)
    icing_obj = parent_to(add_icing_mesh(icing), rig)
    for obj in add_icing_drips(icing):
        parent_to(obj, rig)
    for obj in add_sprinkles(sprinkle_mats):
        parent_to(obj, rig)
    add_bread_texture_dots(rig, toasted)

    set_origin_center(body)
    set_origin_center(icing_obj)
    animate_rig(rig)
    add_camera_and_lights()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 64
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = FPS
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.world.color = (1.0, 1.0, 1.0)
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"


def get_output_dir():
    args = sys.argv
    if "--" in args:
        extra_args = args[args.index("--") + 1 :]
        if "--output-dir" in extra_args:
            index = extra_args.index("--output-dir")
            if index + 1 < len(extra_args):
                return os.path.abspath(extra_args[index + 1])
    return os.path.dirname(os.path.abspath(__file__))


def save_outputs(render_preview=False):
    output_dir = get_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    blend_path = os.path.join(output_dir, "rotating_angled_donut.blend")
    glb_path = os.path.join(output_dir, "rotating_angled_donut.glb")
    preview_path = os.path.join(output_dir, "rotating_angled_donut_preview.png")

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", export_animations=True)

    if render_preview:
        bpy.context.scene.frame_set(32)
        bpy.context.scene.render.filepath = preview_path
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)

    print(f"Saved Blender scene: {blend_path}")
    print(f"Saved animated GLB: {glb_path}")
    if render_preview:
        print(f"Saved PNG preview: {preview_path}")


if __name__ == "__main__":
    create_scene()
    save_outputs(render_preview="--render-preview" in sys.argv)
