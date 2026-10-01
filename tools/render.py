"""Render the actual manufacturing meshes, with illustrative electronics and optics."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyvista as pv
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from design.bucket import BOARD_HOLES, BUCKET_FASTENERS, DIMENSIONS, FACEPLATE_FASTENERS

OUTPUT = ROOT / "renders"
BACKGROUND = "#E4E9EA"
BLACK = "#24282E"
GLOW = "#D5E9A5"


def polydata(mesh):
    faces = np.column_stack((np.full(len(mesh.faces), 3), mesh.faces)).ravel()
    return pv.PolyData(mesh.vertices, faces)


def load_part(name, assembly=True):
    mesh = trimesh.load_mesh(ROOT / "print" / f"{name}.stl")
    if assembly and name == "bucket_glow":
        mesh.vertices = np.column_stack((mesh.vertices[:, 0],
                                        DIMENSIONS.front - mesh.vertices[:, 2],
                                        mesh.vertices[:, 1] + DIMENSIONS.eye_z))
    if assembly and name in ("carrier_black", "guard_black"):
        back = DIMENSIONS.carrier_back if name == "carrier_black" else DIMENSIONS.guard_back_inner + DIMENSIONS.guard_thickness
        horizontal = mesh.vertices[:, 0].copy()
        vertical = mesh.vertices[:, 1] + DIMENSIONS.eye_z
        depth = back - mesh.vertices[:, 2]
        mesh.vertices = np.column_stack((horizontal, depth, vertical))
    if assembly and name.startswith("test_"):
        mesh.apply_translation((0, DIMENSIONS.front, DIMENSIONS.eye_z - 53))
    return polydata(mesh)


def add_solid(plot, mesh, color, shift=(0, 0, 0), opacity=1.0, emissive=False):
    return plot.add_mesh(
        mesh.translate(shift, inplace=False), color=color, opacity=opacity,
        smooth_shading=True, split_sharp_edges=True, feature_angle=35,
        pbr=False, ambient=0.40, diffuse=0.65, specular=0.10, lighting=not emissive,
    )


def add_box(plot, size, center, color, shift=(0, 0, 0), opacity=1.0):
    mesh = pv.Cube(center=center, x_length=size[0], y_length=size[1], z_length=size[2])
    return add_solid(plot, mesh, color, shift, opacity)


def add_cylinder(plot, radius, height, center, color, shift=(0, 0, 0), opacity=1.0):
    mesh = pv.Cylinder(center=center, direction=(0, 1, 0), radius=radius,
                       height=height, resolution=96)
    return add_solid(plot, mesh, color, shift, opacity)


def eye_texture():
    size = 768
    grid_y, grid_x = np.mgrid[-1:1:complex(size), -1:1:complex(size)]
    radius = np.sqrt(grid_x ** 2 + grid_y ** 2)
    angle = np.arctan2(grid_y, grid_x)
    shade = np.clip(1 - 0.30 * radius ** 2 - 0.15 * grid_y, 0.45, 1)
    image = np.stack((shade * 239, shade * 235, shade * 211), axis=-1)
    iris = np.sqrt((grid_x - 0.045) ** 2 + (grid_y + 0.015) ** 2)
    rays = np.sin(angle * 91 + iris * 16) + 0.5 * np.sin(angle * 177 - iris * 40)
    mask = iris < 0.68
    grain = np.clip(0.55 + rays * 0.13 + np.sin(iris * 46) * 0.07, 0, 1)
    image[mask] = np.stack((72 + 88 * grain, 101 + 78 * grain, 27 + 46 * grain), axis=-1)[mask]
    outer = (iris > 0.60) & (iris < 0.68)
    image[outer] *= 0.50
    inner = (iris > 0.22) & (iris < 0.34)
    image[inner, 0] = np.clip(image[inner, 0] * 1.45, 0, 255)
    pupil = (grid_x - 0.045) ** 2 / 0.14 ** 2 + (grid_y + 0.015) ** 2 / 0.50 ** 2 < 1
    image[pupil] = [6, 10, 10]
    reflection = (grid_x + 0.21) ** 2 / 0.13 ** 2 + (grid_y + 0.29) ** 2 / 0.10 ** 2 < 1
    image[reflection] = image[reflection] * 0.20 + np.array([244, 252, 248]) * 0.80
    tiny_reflection = (grid_x - 0.21) ** 2 + (grid_y - 0.27) ** 2 < 0.045 ** 2
    image[tiny_reflection] = [240, 250, 242]
    return pv.numpy_to_texture(np.uint8(np.clip(image, 0, 255)))


def eye_dome(plot, shift=(0, 0, 0), night=False):
    radial_steps, angular_steps = 48, 192
    radial = np.linspace(0, 20.0, radial_steps)
    angle = np.linspace(0, 2 * np.pi, angular_steps)
    radial_grid, angle_grid = np.meshgrid(radial, angle, indexing="ij")
    horizontal = radial_grid * np.cos(angle_grid)
    vertical = radial_grid * np.sin(angle_grid)
    sphere_radius = (20 ** 2 + 16 ** 2) / (2 * 16)
    protrusion = np.sqrt(sphere_radius ** 2 - radial_grid ** 2) - (sphere_radius - 16)
    depth = DIMENSIONS.holder_front + 2.8 - protrusion
    grid = pv.StructuredGrid(horizontal + shift[0], depth + shift[1], vertical + DIMENSIONS.eye_z + shift[2])
    surface = grid.extract_surface(algorithm="dataset_surface")
    surface.active_texture_coordinates = np.column_stack(
        ((surface.points[:, 0] - shift[0]) / 40 + 0.5,
         (surface.points[:, 2] - DIMENSIONS.eye_z - shift[2]) / 40 + 0.5)
    )
    plot.add_mesh(surface, texture=eye_texture(), smooth_shading=True,
                  ambient=0.75 if night else 0.4, diffuse=0.7, specular=0.6,
                  specular_power=70, lighting=not night)


def electronics(plot, shift=(0, 0, 0), eye=True, night=False):
    add_box(plot, (50.8, 1.6, 52), (0, DIMENSIONS.pcb_front + 0.8, DIMENSIONS.eye_z + 3), "#27403D", shift)
    add_box(plot, (27, 1.6, 9), (0, DIMENSIONS.pcb_front + 0.8, DIMENSIONS.eye_z - 27), "#27403D", shift)
    add_box(plot, (30.6, 2.5, 35), (0, DIMENSIONS.pcb_front - 1.25, DIMENSIONS.eye_z + 1.34), "#161B20", shift)
    add_box(plot, (25.5, 0.4, 25.5), (0, DIMENSIONS.pcb_front - 2.7, DIMENSIONS.eye_z), "#060A0B", shift)
    for horizontal in (-17, 17):
        add_box(plot, (4.5, 8.5, 29), (horizontal, DIMENSIONS.pcb_rear + 4.25, DIMENSIONS.eye_z + 2), "#131619", shift)
    add_box(plot, (8, 4, 6), (0, DIMENSIONS.pcb_rear + 2, DIMENSIONS.eye_z + 24), "#ACB3B6", shift)
    add_box(plot, (7, 6, 5), (8, DIMENSIONS.pcb_rear + 3, DIMENSIONS.eye_z + 15), "#EEE9D7", shift)
    holder = pv.Disc(center=(0, DIMENSIONS.holder_front + 1.4, DIMENSIONS.eye_z), inner=19, outer=25.8,
                     normal=(0, -1, 0), r_res=1, c_res=160).extrude((0, -2.8, 0), capping=True)
    add_solid(plot, holder, "#C1DFE3", shift, 0.38)
    for horizontal, vertical in BOARD_HOLES:
        add_cylinder(plot, 2.5, 6, (horizontal, DIMENSIONS.pcb_front - 3, DIMENSIONS.eye_z + vertical), "#ECEBDD", shift)
        add_cylinder(plot, 2.2, 1.6, (horizontal, DIMENSIONS.holder_front - 0.8, DIMENSIONS.eye_z + vertical), "#E1E2D7", shift)
    if eye:
        eye_dome(plot, shift, night)


def battery(plot, shift=(0, 0, 0)):
    center_y = DIMENSIONS.guard_back_inner - 1.0 - DIMENSIONS.battery_thickness / 2
    add_box(plot, (29, 4.75, 36), (0, center_y, 78), "#AFB6BE", shift)
    add_box(plot, (25, 0.2, 23), (0, center_y - 2.5, 77), "#EAEEE9", shift)
    add_box(plot, (29, 4.9, 4), (0, center_y, 94), "#D7A725", shift)
    add_box(plot, (33, 0.9, 9), (0, center_y - 3.1, 80), "#373C42", shift)
    for horizontal, color in ((-1.1, "#A5413A"), (1.1, "#26292B")):
        points = np.array([
            (horizontal, center_y, 96), (horizontal + 6, center_y - 2, 105),
            (25 + horizontal, DIMENSIONS.pcb_rear + 6, 116), (26 + horizontal, DIMENSIONS.pcb_rear + 6, 149),
            (8 + horizontal, DIMENSIONS.pcb_rear + 5, DIMENSIONS.eye_z + 15),
        ]) + shift
        plot.add_mesh(pv.Spline(points, 80).tube(radius=0.55), color=color, smooth_shading=True)


def screw_heads(plot, shift=(0, 0, 0)):
    for horizontal, vertical in BUCKET_FASTENERS:
        add_cylinder(plot, 2.2, 1.5, (horizontal, DIMENSIONS.front - 0.75, DIMENSIONS.eye_z + vertical), "#8C969C", shift)
        add_box(plot, (2.2, 0.15, 0.45), (horizontal, DIMENSIONS.front - 1.55, DIMENSIONS.eye_z + vertical), BLACK, shift)
    for horizontal, vertical in FACEPLATE_FASTENERS:
        front = DIMENSIONS.front - DIMENSIONS.faceplate_thickness
        add_cylinder(plot, 2.6, 0.5, (horizontal, front - 0.25, DIMENSIONS.eye_z + vertical), "#939B9F", shift)
        add_cylinder(plot, 2.0, 1.3, (horizontal, front - 1.15, DIMENSIONS.eye_z + vertical), "#535B61", shift)
        add_box(plot, (2.0, 0.15, 0.45), (horizontal, front - 1.85, DIMENSIONS.eye_z + vertical), BLACK, shift)


def add_ground(plot, night=False):
    floor = pv.Plane(center=(0, 0, -0.55), direction=(0, 0, 1), i_size=1700, j_size=1700)
    plot.add_mesh(floor, color="#171D20" if night else BACKGROUND, lighting=False)


def setup_plot(night=False):
    plot = pv.Plotter(off_screen=True, window_size=(1560, 1040), lighting="none")
    plot.set_background("#171D20" if night else BACKGROUND)
    plot.enable_parallel_projection()
    plot.enable_anti_aliasing("ssaa")
    plot.enable_depth_peeling(number_of_peels=12, occlusion_ratio=0.0)
    for position, intensity in (((-280, -380, 560), 0.85), ((340, -80, 340), 0.5), ((40, 380, 420), 0.8)):
        plot.add_light(pv.Light(position=position, focal_point=(0, 0, 100),
                                color="white", intensity=intensity * (0.13 if night else 1),
                                light_type="scene light"))
    return plot


VIEWS = {
    "01_front_three_quarter": ((310, -470, 290), (0, 0, 102), 146, "CORE ONE+ / SCULPTED CYCLOPS", "Same sculpted skull and cauldron; the replacement carrier accepts M2 x 20 wall screws."),
    "02_front": ((0, -540, 139), (0, 0, 102), 139, "FRONT / SCULPTED SKULL", "Up to 10.5 mm relief thickness / original 3 mm screw seats / unchanged 44.4 mm eye opening."),
    "03_rear": ((-300, 420, 280), (0, 0, 100), 151, "REAR / ROUNDED CAULDRON", "Narrowed neck, rolled lip, and reinforced rope lugs shifted toward the electronics."),
    "04_top_interior": ((200, -330, 490), (0, 0, 100), 155, "TOP / CANDY SPACE", "Removable guard separates the HalloWing, wiring, and battery from candy."),
    "05_cutaway": ((310, -270, 260), (0, -14, 106), 145, "SECTION / SKULL EYE", "Right half removed for inspection. Battery and optics are reference envelopes."),
    "06_mounting_test": ((185, -330, 225), (0, -72, 111), 95, "M2 x 20 CARRIER / FIT TEST", "Same black wall coupon and glow skull; test the new deep-nut carrier before transferring it to the cauldron."),
    "07_exploded_mount": ((340, -390, 310), (0, -5, 118), 166, "EXPLODED / SEPARATE FACEPLATE", "Glow skull > black wall > stock lens + PCB > carrier > battery guard."),
    "08_glow_preview": ((230, -450, 270), (0, 0, 102), 151, "CYCLOPS CAULDRON / GLOW STUDY", "Illustrative charged-phosphor appearance, not a calibrated brightness prediction."),
    "09_printed_parts": ((270, -430, 285), (0, 0, 102), 146, "PRINTED PARTS / NO ELECTRONICS", "Four existing M2 x 10 screws attach the sculpted skull; its back and screw seats stay flat."),
    "10_rope_balance": ((0, 0, 620), (0, 0, 95), 154, "BALANCE / FIXED ROPE HOLES", "Amber: existing rope axis and updated mass-center marker. The printed rope holes do not move."),
    "11_sculpted_closeup": ((150, -240, 290), (0, -16, 2), 90, "SCULPTED FACEPLATE / CLOSE-UP", "Raised forehead, brow, cheekbones, jaw and teeth; 10.5 mm maximum thickness, flat back down."),
    "12_sculpted_front": ((0, -16, 350), (0, -16, 2), 90, "SCULPTED FACEPLATE / FRONT", "Original outline, eye opening and four M2 positions retained. Recessed seats keep M2 x 10 screws."),
    "13_sculpted_raking": ((80, -260, 100), (0, -16, 2), 76, "LOW ANGLE / STRONGER CONTOURS", "The sculpted skull stays unchanged; reprint only the small carrier to use M2 x 20 wall screws."),
}


def compose_caption(path, title, subtitle, night=False):
    rendered = Image.open(path).convert("RGB")
    image = Image.new("RGB", (1560, 1280), "#171D20" if night else BACKGROUND)
    image.paste(rendered, (0, 120))
    draw = ImageDraw.Draw(image)
    font_dir = Path("/usr/share/fonts/truetype/dejavu")
    title_font = ImageFont.truetype(str(font_dir / "DejaVuSans-Bold.ttf"), 25)
    body_font = ImageFont.truetype(str(font_dir / "DejaVuSans.ttf"), 18)
    ink = "#D5E9A5" if night else "#252D32"
    secondary = "#AEBABD" if night else "#526068"
    draw.text((64, 45), "CYCLOPS CAULDRON / CORE ONE+ / REVISION 07", font=body_font, fill=secondary)
    draw.text((64, 80), title, font=title_font, fill=ink)
    draw.line((64, 1180, 1496, 1180), fill=secondary, width=1)
    draw.text((64, 1205), subtitle, font=body_font, fill=secondary)
    if title.startswith("BALANCE"):
        balance = json.loads((ROOT / "docs/validation.json").read_text())["balance"]
        draw.line((64, 168, 108, 168), fill="#829099", width=3)
        draw.text((124, 155), "Geometric center", font=body_font, fill=secondary)
        draw.line((64, 204, 108, 204), fill="#B57A2C", width=4)
        draw.text((124, 191), "Rope / assembled COM", font=body_font, fill=secondary)
        draw.text((64, 248), f"{abs(balance['rope_axis_y_mm']):.2f} mm toward the eye", font=body_font, fill=ink)
        draw.text((64, 280), "Printed rope holes unchanged", font=body_font, fill=secondary)
    image.save(path)


def render_view(name):
    camera, target, scale, title, subtitle = VIEWS[name]
    night = "glow_preview" in name
    plot = setup_plot(night)
    detail_view = name in ("11_sculpted_closeup", "12_sculpted_front", "13_sculpted_raking")
    if detail_view:
        actor = add_solid(plot, load_part("bucket_glow", assembly=False), GLOW)
        actor.prop.ambient = 0.20
        actor.prop.diffuse = 0.85
        actor.prop.specular = 0.10
        for light, position, intensity in zip(plot.renderer.lights,
                ((-180, -50, 105), (150, 80, 230), (0, 200, 80)), (0.95, 0.35, 0.20), strict=True):
            light.position = position
            light.focal_point = (0, -15, 2)
            light.intensity = intensity
    elif name == "07_exploded_mount":
        add_solid(plot, load_part("test_black"), BLACK)
        add_solid(plot, load_part("bucket_glow"), GLOW, (0, -45, 0))
        electronics(plot, (0, 45, 0))
        add_solid(plot, load_part("carrier_black"), BLACK, (0, 88, 0))
        add_solid(plot, load_part("guard_black"), BLACK, (0, 155, 0))
        battery(plot, (0, 155, 0))
        for horizontal, vertical in BUCKET_FASTENERS:
            plot.add_mesh(pv.Line((horizontal, DIMENSIONS.front + 5, DIMENSIONS.eye_z + vertical),
                                  (horizontal, DIMENSIONS.carrier_back + 90, DIMENSIONS.eye_z + vertical)),
                          color="#7B8C93", line_width=1, opacity=0.40)
    elif name == "06_mounting_test":
        add_solid(plot, load_part("test_black"), BLACK)
        add_solid(plot, load_part("bucket_glow"), GLOW)
        add_solid(plot, load_part("carrier_black"), BLACK)
        electronics(plot)
        screw_heads(plot)
    else:
        shell = load_part("bucket_black")
        ornament = load_part("bucket_glow")
        if name == "05_cutaway":
            shell = shell.clip(normal=(1, 0, 0), origin=(0, 0, 0), invert=True)
            ornament = ornament.clip(normal=(1, 0, 0), origin=(0, 0, 0), invert=True)
        add_solid(plot, shell, BLACK)
        add_solid(plot, ornament, "#C1F68B" if night else GLOW, emissive=night)
        if name != "09_printed_parts":
            add_solid(plot, load_part("carrier_black"), BLACK)
            cover = load_part("guard_black")
            if name == "05_cutaway":
                cover = cover.clip(normal=(1, 0, 0), origin=(0, 0, 0), invert=True)
            add_solid(plot, cover, BLACK)
            electronics(plot, night=night)
            battery(plot)
            screw_heads(plot)
        else:
            screw_heads(plot)
        if name == "10_rope_balance":
            balance = json.loads((ROOT / "docs/validation.json").read_text())["balance"]
            rope_y = balance["rope_axis_y_mm"]
            overlay_z = DIMENSIONS.height + 2
            plot.add_mesh(pv.Line((-126, 0, overlay_z), (126, 0, overlay_z)),
                          color="#829099", line_width=2, lighting=False)
            plot.add_mesh(pv.Line((-126, rope_y, overlay_z), (126, rope_y, overlay_z)),
                          color="#B57A2C", line_width=3, lighting=False)
            for horizontal, depth, _ in balance["anchor_centers_mm"]:
                plot.add_mesh(pv.Sphere(radius=3.0, center=(horizontal, depth, overlay_z)),
                              color="#B57A2C", lighting=False)
            center_x, center_y, _ = balance["assembled_center_mm"]
            cross = pv.Disc(center=(center_x, center_y, overlay_z + 1), inner=3, outer=4.2,
                            normal=(0, 0, 1), r_res=1, c_res=60)
            plot.add_mesh(cross, color="#B57A2C", lighting=False)
    if name not in ("06_mounting_test", "07_exploded_mount") and not detail_view:
        add_ground(plot, night)
    plot.camera_position = [camera, target, (0, 1, 0) if name in ("10_rope_balance", "12_sculpted_front") else (0, 0, 1)]
    plot.camera.parallel_scale = scale
    path = OUTPUT / f"{name}.png"
    plot.show(screenshot=str(path), auto_close=True)
    compose_caption(path, title, subtitle, night)
    image = np.array(Image.open(path))
    center = image[180:1100, 200:1360]
    assert np.std(center) > 14, f"Blank or uninformative render: {name}"
    assert len(np.unique(center[::12, ::12].reshape(-1, 3), axis=0)) > 80
    print(f"Rendered {path.name}", flush=True)
    return {"image": path.name, "size": list(image.shape[:2][::-1]), "nonblank": True,
            "camera": camera, "target": target}


def contact_sheet():
    files = [OUTPUT / f"{name}.png" for name in VIEWS
             if name != "07_exploded_mount" and (OUTPUT / f"{name}.png").exists()]
    sheet = Image.new("RGB", (1560, 1280 * ((len(files) + 2) // 3) // 3), BACKGROUND)
    for index, path in enumerate(files):
        thumb = Image.open(path).convert("RGB").resize((520, 426), Image.Resampling.LANCZOS)
        sheet.paste(thumb, ((index % 3) * 520, (index // 3) * 426))
    sheet.save(OUTPUT / "overview.png")
    details = ("11_sculpted_closeup", "12_sculpted_front", "13_sculpted_raking", "01_front_three_quarter")
    if all((OUTPUT / f"{name}.png").exists() for name in details):
        sheet = Image.new("RGB", (1560, 1280), BACKGROUND)
        for index, name in enumerate(details):
            thumb = Image.open(OUTPUT / f"{name}.png").convert("RGB").resize((780, 640), Image.Resampling.LANCZOS)
            sheet.paste(thumb, ((index % 2) * 780, (index // 2) * 640))
        sheet.save(OUTPUT / "faceplate_overview.png")


PRINT_BED_TITLES = {
    "01_mount_test_black.3mf": "01 / MOUNTING TEST / BLACK PLA",
    "02_skull_faceplate_glow.3mf": "02 / SCULPTED SKULL / GLOW PLA",
    "03_carrier_black.3mf": "03 / M2 x 20 CARRIER / BLACK PLA",
    "04_guard_black.3mf": "04 / BATTERY GUARD / BLACK PLA",
    "05_cauldron_black.3mf": "05 / CAULDRON / BLACK PLA",
}
PRINT_BED_OUTPUT = OUTPUT / "print_beds"
SUPPORT_COLOR = "#C67B36"


def file_sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def gcode_print_features(path):
    coordinates = np.zeros(3)
    selected_feature = None
    started = False
    features = {"support": [], "brim": []}
    number = re.compile(r"([XYZE])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.startswith(";LAYER_CHANGE"):
                started = True
            if line.startswith(";TYPE:"):
                feature = line[6:].strip().lower()
                selected_feature = "support" if "support" in feature else "brim" if feature == "skirt/brim" else None
            executable = line.split(";", 1)[0].strip()
            if not executable.startswith(("G0 ", "G1 ")):
                continue
            parameters = {axis: float(value) for axis, value in number.findall(executable)}
            previous = coordinates.copy()
            for index, axis in enumerate("XYZ"):
                if axis in parameters:
                    coordinates[index] = parameters[axis]
            if (started and selected_feature and parameters.get("E", 0) > 0
                    and np.linalg.norm(coordinates[:2] - previous[:2]) > 1e-6):
                features[selected_feature].append((previous, coordinates.copy()))
    return {name: np.asarray(segments, dtype=float).reshape(-1, 2, 3) for name, segments in features.items()}


def add_core_one_bed(plot):
    add_box(plot, (258, 228, 5), (125, 110, -3.6), "#343D43")
    add_box(plot, (250, 220, 1.0), (125, 110, -0.55), "#879295")
    for horizontal in range(0, 251, 10):
        plot.add_mesh(pv.Line((horizontal, 0, -0.025), (horizontal, 220, -0.025)),
                      color="#C2C9C9" if horizontal % 50 == 0 else "#A6B0B1", line_width=1, lighting=False)
    for depth in range(0, 221, 10):
        plot.add_mesh(pv.Line((0, depth, -0.025), (250, depth, -0.025)),
                      color="#C2C9C9" if depth % 50 == 0 else "#A6B0B1", line_width=1, lighting=False)
    border = pv.MultipleLines(np.array([(0, 0, 0), (250, 0, 0), (250, 220, 0), (0, 220, 0), (0, 0, 0)]))
    plot.add_mesh(border, color="#E9ECE8", line_width=2, lighting=False)
    for label, center, width in (("CORE ONE+", (125, -22, 0.3), 81),
                                  ("250 x 220 mm", (125, 233, 0.3), 66),
                                  ("FRONT / Y = 0", (125, -37, 0.3), 53)):
        text = pv.Text3D(label, depth=0.02, width=width, center=center, normal=(0, 0, 1))
        plot.add_mesh(text, color="#354249", lighting=False)


def add_print_features(plot, features):
    for segments in features.values():
        if not len(segments):
            continue
        points = segments.reshape(-1, 3)
        lines = np.column_stack((np.full(len(segments), 2), np.arange(len(points)).reshape(-1, 2))).ravel()
        paths = pv.PolyData(points, lines=lines)
        plot.add_mesh(paths, color=SUPPORT_COLOR, line_width=2, render_lines_as_tubes=True, lighting=False)


def render_print_bed(filename, job):
    source = ROOT / "print" / filename
    gcode = ROOT / job["gcode_file"]
    if file_sha256(source) != job["sha256"] or file_sha256(gcode) != job["gcode_sha256"]:
        raise ValueError(f"Print/G-code changed since validation: {filename}")
    mesh = trimesh.load(source, force="scene").to_geometry()
    if not isinstance(mesh, trimesh.Trimesh) or not mesh.is_watertight:
        raise ValueError(f"Expected a closed placed print mesh: {filename}")
    if np.any(mesh.bounds[0] < -0.001) or np.any(mesh.bounds[1] > [250.001, 220.001, 270.001]):
        raise ValueError(f"Placed model is outside the CORE One+ bed: {filename}")
    if abs(mesh.bounds[0, 2]) > 0.001:
        raise ValueError("The print is not resting on the bed")
    features = gcode_print_features(gcode)
    audit_bounds = np.asarray(job["gcode_audit"]["deposition_bounds_mm"])
    for name, segments in features.items():
        if len(segments):
            points = segments.reshape(-1, 3)
            assert np.all(points >= audit_bounds[0] - 0.001) and np.all(points <= audit_bounds[1] + 0.001)
        if name == "support" and not job["supports"]:
            assert len(segments) == 0
        if name == "brim" and not job["brim_mm"]:
            assert len(segments) == 0
    plot = setup_plot()
    for light in plot.renderer.lights:
        light.focal_point = (125, 110, 70)
    add_core_one_bed(plot)
    add_solid(plot, polydata(mesh), GLOW if job["material"] == "glow" else BLACK)
    add_print_features(plot, features)
    plot.camera_position = [(470, -410, 490), (125, 110, 55), (0, 0, 1)]
    plot.camera.parallel_scale = 205
    image_path = PRINT_BED_OUTPUT / (source.stem + ".png")
    plot.show(screenshot=str(image_path), auto_close=True)
    audit = job["gcode_audit"]
    subtitle = f"{Path(job['gcode_file']).name} | {audit['filament_g']:.2f} g | {audit['estimated_time']}"
    compose_caption(image_path, PRINT_BED_TITLES[filename], subtitle)
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    if any(len(segments) for segments in features.values()):
        legend = "Amber = actual G-code supports / brim; printed in the job's filament."
        draw.line((64, 164, 104, 164), fill=SUPPORT_COLOR, width=5)
        draw.text((118, 150), legend, fill="#526068", font=font)
    else:
        draw.text((64, 150), "No supports or brim in this job.", fill="#526068", font=font)
    draw.text((64, 181), "Dimensioned bed reference; exact 3MF placement, no assembly hardware.", fill="#526068", font=font)
    image.save(image_path)
    pixels = np.asarray(image)[230:1120, 170:1400]
    assert np.std(pixels) > 18 and len(np.unique(pixels[::15, ::15].reshape(-1, 3), axis=0)) > 100
    print(f"Rendered print bed: {source.stem}; supports={len(features['support'])}, brim={len(features['brim'])}", flush=True)
    return {
        "image": image_path.name, "source_3mf": str(source.relative_to(ROOT)),
        "source_3mf_sha256": job["sha256"], "gcode": job["gcode_file"], "gcode_sha256": job["gcode_sha256"],
        "placed_model_bounds_mm": mesh.bounds.tolist(), "printable_bed_mm": [250, 220],
        "assembly_transforms_applied": False, "camera_position": [list(value) for value in plot.camera_position],
        "support_segments": len(features["support"]), "brim_segments": len(features["brim"]),
        "bed_visualization": "Dimensioned reference sheet, not an exact model of the printer chassis",
        "nonblank": True,
    }


def print_bed_contact_sheet():
    sheet = Image.new("RGB", (1560, 1920), BACKGROUND)
    for index, filename in enumerate(PRINT_BED_TITLES):
        path = PRINT_BED_OUTPUT / (Path(filename).stem + ".png")
        if path.exists():
            thumbnail = Image.open(path).convert("RGB").resize((780, 640), Image.Resampling.LANCZOS)
            sheet.paste(thumbnail, ((index % 2) * 780, (index // 2) * 640))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    draw.text((834, 1450), "FIVE SEPARATE PRINT JOBS", fill="#253239", font=title_font)
    for index, text in enumerate(("CORE One+ / 250 x 220 mm print area",
                                   "Identical camera scale in all five views.",
                                   "Positions and orientations come from the 3MFs.",
                                   "Amber paths come from the matching G-code.",
                                   "Supports/brims use the same filament as the part.",
                                   "Only job 02 uses glow filament.")):
        draw.text((834, 1510 + index * 40), text, fill="#526068", font=font)
    sheet.save(PRINT_BED_OUTPUT / "overview.png")


def render_print_beds(jobs=None):
    report = json.loads((ROOT / "docs/slicer_validation.json").read_text())
    assert set(report["plates"]) == set(PRINT_BED_TITLES)
    PRINT_BED_OUTPUT.mkdir(parents=True, exist_ok=True)
    results = [render_print_bed(filename, report["plates"][filename])
               for index, filename in enumerate(PRINT_BED_TITLES, start=1) if not jobs or index in jobs]
    manifest_path = PRINT_BED_OUTPUT / "manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    by_image = {record["image"]: record for record in previous}
    by_image.update({record["image"]: record for record in results})
    manifest_path.write_text(json.dumps(sorted(by_image.values(), key=lambda record: record["image"]), indent=2) + "\n")
    print_bed_contact_sheet()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--views", nargs="*", choices=VIEWS)
    selection.add_argument("--print-beds", action="store_true")
    parser.add_argument("--jobs", nargs="+", type=int, choices=range(1, 6))
    arguments = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    if arguments.print_beds:
        render_print_beds(arguments.jobs)
    else:
        if arguments.jobs:
            parser.error("--jobs requires --print-beds")
        results = [render_view(name) for name in (arguments.views or VIEWS)]
        contact_sheet()
        (OUTPUT / "render_manifest.json").write_text(json.dumps(results, indent=2) + "\n")