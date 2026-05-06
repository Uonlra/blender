import math
import os
import sys

import bpy
from mathutils import Vector


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_mat(name, color, metallic=0.0, roughness=0.45, emission=None, strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission:
            emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
            if emission_input:
                emission_input.default_value = emission
            strength_input = bsdf.inputs.get("Emission Strength")
            if strength_input:
                strength_input.default_value = strength
    return mat


def cube_obj(name, location, scale, mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new(name="softened_edges", type="BEVEL")
        mod.width = bevel
        mod.segments = 2
        obj.modifiers.new(name="weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def cylinder_obj(name, location, radius, depth, mat=None, vertices=24, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    obj.modifiers.new(name="weighted_normals", type="WEIGHTED_NORMAL")
    return obj


def add_area_light(name, location, power, size, rotation):
    bpy.ops.object.light_add(type="AREA", location=location, rotation=rotation)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.size = size
    return light


def add_label(text, location, size, mat, rotation=(math.radians(70), 0, 0)):
    bpy.ops.object.text_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = f"label_{text.lower().replace(' ', '_')}"
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.005
    obj.data.materials.append(mat)
    return obj


def create_console():
    clear_scene()

    metal = make_mat("gunmetal", (0.08, 0.09, 0.1, 1), metallic=0.6, roughness=0.35)
    dark = make_mat("matte_black", (0.01, 0.012, 0.014, 1), roughness=0.7)
    panel = make_mat("deep_panel", (0.025, 0.035, 0.045, 1), metallic=0.2, roughness=0.55)
    blue = make_mat(
        "cyan_emission",
        (0.0, 0.55, 0.95, 1),
        emission=(0.0, 0.75, 1.0, 1),
        strength=3.5,
    )
    amber = make_mat(
        "amber_emission",
        (1.0, 0.42, 0.05, 1),
        emission=(1.0, 0.34, 0.02, 1),
        strength=2.2,
    )
    red = make_mat(
        "red_emission",
        (1.0, 0.05, 0.04, 1),
        emission=(1.0, 0.03, 0.02, 1),
        strength=2.5,
    )
    green = make_mat(
        "green_emission",
        (0.25, 1.0, 0.32, 1),
        emission=(0.1, 1.0, 0.25, 1),
        strength=2.5,
    )
    glass = make_mat(
        "hologram_translucent_cyan",
        (0.0, 0.75, 1.0, 0.28),
        emission=(0.0, 0.6, 1.0, 1),
        strength=1.8,
    )
    glass.blend_method = "BLEND"
    glass.use_screen_refraction = True
    glass.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.28

    floor = cube_obj("floor_plate", (0, 0, -0.08), (7.5, 6.0, 0.12), dark, bevel=0.03)
    wall = cube_obj("rear_wall", (0, 2.35, 1.35), (7.5, 0.16, 2.8), panel, bevel=0.02)
    wall.data.materials[0] = panel

    for x in [-3, -1.5, 0, 1.5, 3]:
        cube_obj("floor_light_strip", (x, -0.75, -0.005), (0.05, 4.0, 0.025), blue, bevel=0.01)
    for x in [-2.8, 0, 2.8]:
        cube_obj("wall_vertical_panel", (x, 2.25, 1.42), (0.08, 0.08, 2.25), metal, bevel=0.01)
    for z in [0.45, 1.25, 2.05]:
        cube_obj("wall_glow_line", (0, 2.17, z), (6.8, 0.035, 0.025), blue, bevel=0.008)

    cube_obj("console_base", (0, 0, 0.3), (4.5, 1.65, 0.65), metal, bevel=0.09)
    deck = cube_obj("slanted_control_deck", (0, -0.18, 0.82), (4.25, 1.35, 0.18), panel, bevel=0.06)
    deck.rotation_euler[0] = math.radians(-10)

    cube_obj("left_support", (-1.65, 0.28, 0.96), (0.55, 0.42, 0.72), metal, bevel=0.05)
    cube_obj("right_support", (1.65, 0.28, 0.96), (0.55, 0.42, 0.72), metal, bevel=0.05)
    cube_obj("screen_stem", (0, 0.37, 1.24), (0.35, 0.28, 0.8), metal, bevel=0.04)

    screen_frame = cube_obj("main_screen_frame", (0, 0.52, 1.78), (2.2, 0.12, 1.1), metal, bevel=0.06)
    screen_frame.rotation_euler[0] = math.radians(8)
    screen = cube_obj("main_blue_screen", (0, 0.45, 1.78), (1.9, 0.035, 0.82), blue, bevel=0.025)
    screen.rotation_euler[0] = math.radians(8)

    for i, z in enumerate([1.58, 1.78, 1.98]):
        cube_obj(f"screen_scanline_{i + 1}", (0, 0.41, z), (1.65, 0.02, 0.025), dark, bevel=0.004)
    for i, x in enumerate([-0.65, 0, 0.65]):
        cube_obj(f"screen_data_block_{i + 1}", (x, 0.405, 1.68), (0.38, 0.018, 0.18), amber, bevel=0.008)

    button_mats = [red, amber, green, blue]
    for row, y in enumerate([-0.7, -0.46, -0.22]):
        for col, x in enumerate([-1.45, -1.15, -0.85, -0.55]):
            mat = button_mats[(row + col) % len(button_mats)]
            cylinder_obj(
                f"lit_button_{row + 1}_{col + 1}",
                (x, y, 0.98),
                0.075,
                0.035,
                mat,
                vertices=20,
                rotation=(math.radians(90), 0, 0),
            )

    for i, x in enumerate([0.35, 0.65, 0.95, 1.25]):
        slider = cube_obj(f"slider_track_{i + 1}", (x, -0.52, 0.99), (0.08, 0.62, 0.035), dark, bevel=0.01)
        slider.rotation_euler[0] = math.radians(-10)
        knob_y = -0.76 + i * 0.16
        cube_obj(f"slider_knob_{i + 1}", (x, knob_y, 1.05), (0.18, 0.08, 0.06), amber, bevel=0.015)

    cylinder_obj(
        "large_dial_outer",
        (1.68, -0.54, 1.02),
        0.22,
        0.05,
        metal,
        vertices=40,
        rotation=(math.radians(90), 0, 0),
    )
    cylinder_obj(
        "large_dial_glow",
        (1.68, -0.57, 1.025),
        0.14,
        0.035,
        blue,
        vertices=40,
        rotation=(math.radians(90), 0, 0),
    )

    lever_base = cylinder_obj(
        "lever_base",
        (-1.9, -0.45, 1.0),
        0.18,
        0.05,
        metal,
        vertices=32,
        rotation=(math.radians(90), 0, 0),
    )
    lever_base.rotation_euler[0] = math.radians(80)
    lever = cylinder_obj(
        "lever_handle",
        (-1.9, -0.36, 1.23),
        0.045,
        0.55,
        metal,
        vertices=16,
        rotation=(math.radians(20), 0, 0),
    )
    lever.rotation_euler[0] = math.radians(20)
    cylinder_obj("lever_tip", (-1.9, -0.16, 1.48), 0.09, 0.11, red, vertices=20)

    for i, x in enumerate([-0.55, -0.28, 0.0, 0.28, 0.55]):
        cube_obj(f"mini_key_{i + 1}", (x, -0.88, 0.94), (0.18, 0.1, 0.05), metal, bevel=0.012)

    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=0.72, fill_type="TRIFAN", location=(0, -0.28, 1.58))
    holo = bpy.context.object
    holo.name = "floating_hologram_disc"
    holo.rotation_euler[0] = math.radians(75)
    holo.data.materials.append(glass)

    for radius in [0.32, 0.52, 0.72]:
        bpy.ops.mesh.primitive_torus_add(
            major_radius=radius,
            minor_radius=0.008,
            major_segments=80,
            minor_segments=6,
            location=(0, -0.28, 1.6 + radius * 0.18),
            rotation=(math.radians(75), 0, 0),
        )
        ring = bpy.context.object
        ring.name = f"hologram_ring_{radius:.2f}"
        ring.data.materials.append(blue)

    # Bezier curves make quick cable runs without needing custom mesh vertices.
    cable_mat = make_mat("rubber_cable", (0.005, 0.005, 0.006, 1), roughness=0.9)
    for i, x in enumerate([-2.0, -1.75, 1.75, 2.0]):
        curve = bpy.data.curves.new(f"rear_cable_curve_{i + 1}", "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 16
        curve.bevel_depth = 0.025
        curve.bevel_resolution = 4
        spline = curve.splines.new("BEZIER")
        spline.bezier_points.add(2)
        points = [
            (x, 0.45, 0.65),
            (x * 0.92, 1.25, 0.95),
            (x * 0.82, 2.15, 0.55),
        ]
        for point, co in zip(spline.bezier_points, points):
            point.co = Vector(co)
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
        obj = bpy.data.objects.new(f"rear_cable_{i + 1}", curve)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(cable_mat)

    add_label("NAV", (-0.98, -0.95, 1.02), 0.12, blue)
    add_label("CORE", (0.0, -0.98, 1.02), 0.12, amber)
    add_label("AUX", (0.92, -0.95, 1.02), 0.12, green)

    add_area_light("large_softbox", (0, -3.2, 4.2), 450, 5.0, (math.radians(60), 0, 0))
    add_area_light("cyan_console_glow", (0, -0.9, 1.8), 140, 2.0, (math.radians(75), 0, 0))
    bpy.ops.object.light_add(type="POINT", location=(0, 0.1, 2.2))
    point = bpy.context.object
    point.name = "screen_light_spill"
    point.data.color = (0.1, 0.75, 1.0)
    point.data.energy = 85

    bpy.ops.object.camera_add(location=(3.9, -4.4, 2.7), rotation=(math.radians(62), 0, math.radians(42)))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    camera.data.lens = 35
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = screen
    camera.data.dof.aperture_fstop = 5.6

    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.world.color = (0.005, 0.007, 0.01)
    bpy.context.scene.render.resolution_x = 1600
    bpy.context.scene.render.resolution_y = 1000


def get_output_dir():
    args = sys.argv
    if "--" in args:
        extra_args = args[args.index("--") + 1 :]
        if "--output-dir" in extra_args:
            index = extra_args.index("--output-dir")
            if index + 1 < len(extra_args):
                return os.path.abspath(extra_args[index + 1])
    return os.path.dirname(os.path.abspath(__file__))


def save_outputs():
    output_dir = get_output_dir()
    os.makedirs(output_dir, exist_ok=True)
    blend_path = os.path.join(output_dir, "sci_fi_console.blend")
    glb_path = os.path.join(output_dir, "sci_fi_console.glb")

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB")
    print(f"Saved Blender scene: {blend_path}")
    print(f"Saved GLB model: {glb_path}")


if __name__ == "__main__":
    create_console()
    save_outputs()
