"""Build, render and slice only the compatible sculpted-skull replacement."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import cadquery as cq
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from design.bucket import DIMENSIONS, mass_properties, solid_volume
from design.sculpted_faceplate import assembled_plate, original_plate, sculpted_plate, verify_compatibility
from tools.build import check_plate, mesh_from_shape, write_3mf
from tools.check_slicer import invoke, validate_gcode
from tools.render import (
    BACKGROUND, BLACK, GLOW, add_core_one_bed, add_solid, battery, electronics,
    gcode_print_features, load_part, polydata, screw_heads, setup_plot,
)


BASELINE_COMMIT = "731c8d090d9382937c2cf054e11159906f80cf2b"
OUTPUT = ROOT / "variants/sculpted_skull"
RENDERS = OUTPUT / "renders"
PROTECTED_PATHS = (
    "design/bucket.py", "tools/build.py", "tools/check_slicer.py", "tools/render.py",
    "cad", "print", "profiles", "usb", "docs", "renders", "requirements.txt",
)
PLATE_NAME = "skull_sculpted_glow"
GCODE_NAME = "skull_sculpted_COREONE_04HF_PLA.gcode"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_baseline():
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", BASELINE_COMMIT, "--", *PROTECTED_PATHS],
        cwd=ROOT, text=True,
    ).strip()
    if changed:
        raise ValueError("Existing production files changed; compatibility baseline is no longer fixed:\n" + changed)
    original_report = json.loads((ROOT / "docs/validation.json").read_text())
    for filename, digest in original_report["files_sha256"].items():
        if sha256(ROOT / "print" / filename) != digest:
            raise ValueError(f"Original print export changed: {filename}")
    return original_report


def fixed_hardware_checks():
    installed = assembled_plate()
    collisions = {}
    for name, back in (("bucket_black", None), ("carrier_black", DIMENSIONS.carrier_back),
                       ("guard_black", DIMENSIONS.guard_back_inner + DIMENSIONS.guard_thickness)):
        existing = cq.importers.importStep(str(ROOT / "cad" / f"{name}.step")).val()
        if back is not None:
            existing = existing.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, back, DIMENSIONS.eye_z))
        overlap = solid_volume(installed.intersect(existing))
        assert overlap < 1e-5, f"Replacement overlaps existing {name}"
        collisions[name] = overlap
    return collisions


def fixed_rope_balance(original_report):
    components = [dict(component) for component in original_report["balance"]["components"]]
    volume, center = mass_properties(assembled_plate())
    for component in components:
        if component["name"] == "One-eyed glow skull":
            old_mass = component["mass_g"]
            component.update(mass_g=volume * 1.50 / 1000, center_mm=center)
            added_mass = component["mass_g"] - old_mass
            break
    else:
        raise ValueError("Original faceplate mass component not found")
    total_mass = sum(component["mass_g"] for component in components)
    moment = sum((component["mass_g"] * np.asarray(component["center_mm"]) for component in components), np.zeros(3))
    center = moment / total_mass
    rope_y = original_report["balance"]["rope_axis_y_mm"]
    rope_z = original_report["balance"]["rope_axis_z_mm"]
    tilt = math.degrees(math.atan2(center[1] - rope_y, rope_z - center[2]))
    return {
        "existing_rope_axis_mm": [rope_y, rope_z], "rope_holes_not_repositioned": True,
        "added_mass_at_nominal_glow_density_g": added_mass,
        "assembled_center_mm": center.tolist(), "nominal_empty_pitch_degrees": tilt,
        "scope": "Estimate at 1.50 g/cm3 glow using the original installed-hardware mass assumptions; hang-test required",
    }


def build_variant():
    original_report = verify_baseline()
    checks = verify_compatibility()
    checks["collisions_with_existing_step_parts_mm3"] = fixed_hardware_checks()
    mesh = mesh_from_shape(sculpted_plate())
    original_mesh = trimesh.load_mesh(ROOT / "print/bucket_glow.stl")
    assert np.allclose(mesh.bounds[:, :2], original_mesh.bounds[:, :2], atol=0.002)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mesh.export(OUTPUT / "skull_sculpted.stl")
    step_path = OUTPUT / "skull_sculpted.step"
    cq.exporters.export(sculpted_plate(), str(step_path))
    step_path.write_text("\n".join(line.rstrip(" \t") for line in step_path.read_text().splitlines()) + "\n")
    restored = cq.importers.importStep(str(step_path)).val()
    assert restored.isValid() and abs(solid_volume(restored) - solid_volume(sculpted_plate())) < 1e-3
    center = mesh.bounds.mean(axis=0)
    placement = [125 - center[0], 110 - center[1], 0]
    objects = [("Sculpted skull - existing M2 mount", [PLATE_NAME], placement)]
    plate_path = OUTPUT / "skull_sculpted.3mf"
    write_3mf(plate_path, objects, {PLATE_NAME: mesh})
    check_plate(plate_path, {PLATE_NAME: mesh}, objects)
    placed = trimesh.load(plate_path, force="scene").to_geometry()
    assert placed.is_watertight and np.all(placed.bounds[0] >= -0.001)
    assert np.all(placed.bounds[1] < [250, 220, 270])
    report = {
        "design": "Sculpted skull replacement, experiment 1", "baseline_commit": BASELINE_COMMIT,
        "changes": "Outward relief only; original 3 mm layer, mounting seats, holes and eye bezel retained",
        "compatibility": checks, "mesh": {"watertight": True, "winding_consistent": bool(mesh.is_winding_consistent),
                                            "bounds_mm": mesh.bounds.tolist(), "triangles": len(mesh.faces)},
        "existing_rope_balance": fixed_rope_balance(original_report),
        "density_upper_g_cm3": 2.0,
        "solid_mass_upper_g": solid_volume(sculpted_plate()) * 2.0 / 1000,
        "original_files_unchanged": True,
        "protected_paths": list(PROTECTED_PATHS),
        "baseline_part_hashes": {name: sha256(ROOT / name) for name in (
            "print/bucket_black.stl", "print/carrier_black.stl", "print/guard_black.stl",
            "print/bucket_glow.stl", "cad/bucket_black.step", "cad/carrier_black.step",
        )},
        "files_sha256": {name: sha256(OUTPUT / name) for name in ("skull_sculpted.stl", "skull_sculpted.step", "skull_sculpted.3mf")},
    }
    (OUTPUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"compatibility": checks, "balance": report["existing_rope_balance"]}, indent=2), flush=True)


def slice_variant(executable):
    verify_baseline()
    report = json.loads((OUTPUT / "validation.json").read_text())
    plate_path = OUTPUT / "skull_sculpted.3mf"
    assert sha256(plate_path) == report["files_sha256"][plate_path.name]
    environment = dict(os.environ)
    version = invoke(executable, ["--help"], environment).splitlines()[0]
    if not version.startswith("PrusaSlicer-2.9.6"):
        raise ValueError("This pinned job requires PrusaSlicer 2.9.6")
    profile = ROOT / "profiles/core_one_plus_0.4HF_glow_PLA.ini"
    cache = ROOT / ".cache/sculpted-faceplate"
    cache.mkdir(parents=True, exist_ok=True)
    common = [
        "--config-compatibility", "disable", "--load", profile, "--dont-arrange", "--threads", "4",
        "--layer-height", "0.10", "--first-layer-height", "0.20", "--fill-density", "100%",
        "--fill-pattern", "rectilinear", "--top-solid-layers", "10", "--bottom-solid-layers", "10",
        "--no-support-material", "--brim-width", "0",
    ]
    native = cache / "native.3mf"
    invoke(executable, [*common, "--export-3mf", "--output", native, plate_path], environment)
    with ZipFile(native) as archive:
        config = ET.fromstring(archive.read("Metadata/Slic3r_PE_model.config"))
    assignments = [entry.get("value") for entry in config.findall("object/volume/metadata[@key='extruder']")]
    assert assignments == ["1"]
    native_mesh = trimesh.load(native, force="scene").to_geometry()
    source_mesh = trimesh.load(plate_path, force="scene").to_geometry()
    assert np.allclose(native_mesh.extents, source_mesh.extents, atol=0.02)
    gcode = cache / GCODE_NAME
    output = invoke(executable, [*common, "--export-gcode", "--output", gcode, plate_path], environment)
    (cache / "slicer.log").write_text(output)
    generated = gcode.read_text()
    contents = "\n".join(line.rstrip(" \t") for line in generated.splitlines()) + "\n"
    assert [line.split(";", 1)[0].strip() for line in generated.splitlines()] == [
        line.split(";", 1)[0].strip() for line in contents.splitlines()
    ], "Formatting changed executable G-code"
    audit = validate_gcode(contents, "glow")
    assert audit["layer_count"] >= 50 and audit["filament_g"] < 1000
    assert 6.0 <= audit["deposition_bounds_mm"][1][2] <= 6.3
    assert all(len(segments) == 0 for segments in gcode_print_features(gcode).values()), "Unexpected supports or brim"
    mutations = (
        contents.replace(";LAYER_CHANGE", ";LAYER_CHANGE\nT1", 1),
        contents.replace(";LAYER_CHANGE", ";LAYER_CHANGE\nG1 X251 Y100 E1", 1),
        contents.replace("M104 S220", "M104 S280", 1),
        contents.replace("G29 A ; activate mbl", "; removed mesh activation", 1),
    )
    for mutation in mutations:
        assert mutation != contents
        try:
            validate_gcode(mutation, "glow")
        except ValueError:
            continue
        raise AssertionError("Invalid glow G-code was accepted")
    (OUTPUT / GCODE_NAME).write_text(contents)
    report["gcode"] = {
        "file": GCODE_NAME, "sha256": sha256(OUTPUT / GCODE_NAME), "audit": audit,
        "slicer_version": version, "profile": str(profile.relative_to(ROOT)), "profile_sha256": sha256(profile),
        "overrides": {"layer_height_mm": 0.10, "first_layer_mm": 0.20, "infill_percent": 100,
                      "fill_pattern": "rectilinear", "top_bottom_layers": 10, "supports": False, "brim_mm": 0},
        "native_single_extruder_round_trip": True, "unsafe_mutations_rejected": len(mutations),
        "postprocessing": "Trailing whitespace removed; executable commands verified unchanged",
        "requirements": "CORE One+ / 0.4 mm wear-resistant high-flow / PLA at 220-215 C / smooth PEI at 60 C",
        "user_setup_confirmation": "Same conditional setup as the existing jobs; no new hardware/material details supplied",
    }
    (OUTPUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["gcode"], indent=2), flush=True)


def mesh_in_assembly(mesh):
    transformed = mesh.copy()
    transformed.vertices = np.column_stack((mesh.vertices[:, 0], DIMENSIONS.front - mesh.vertices[:, 2],
                                            DIMENSIONS.eye_z + mesh.vertices[:, 1]))
    return transformed


def caption(path, title, detail):
    rendered = Image.open(path).convert("RGB")
    image = Image.new("RGB", (1560, 1280), BACKGROUND)
    image.paste(rendered, (0, 120))
    draw = ImageDraw.Draw(image)
    fonts = Path("/usr/share/fonts/truetype/dejavu")
    body = ImageFont.truetype(str(fonts / "DejaVuSans.ttf"), 20)
    heading = ImageFont.truetype(str(fonts / "DejaVuSans-Bold.ttf"), 27)
    draw.text((64, 38), "CYCLOPS / SHALLOW RELIEF EXPERIMENT", font=body, fill="#526068")
    draw.text((64, 75), title, font=heading, fill="#253239")
    draw.line((64, 1180, 1496, 1180), fill="#8A979C", width=1)
    assert draw.textlength(detail, font=body) < 1430, "Caption exceeds image width"
    draw.text((64, 1207), detail, font=body, fill="#526068")
    image.save(path)


def render_variant():
    verify_baseline()
    report = json.loads((OUTPUT / "validation.json").read_text())
    assert sha256(OUTPUT / "skull_sculpted.stl") == report["files_sha256"]["skull_sculpted.stl"]
    sculpted = trimesh.load_mesh(OUTPUT / "skull_sculpted.stl")
    original = trimesh.load_mesh(ROOT / "print/bucket_glow.stl")
    RENDERS.mkdir(parents=True, exist_ok=True)
    views = (
        ("01_original_oblique", "ORIGINAL / FLAT 3 MM PLATE", "Original main-branch faceplate, shown at the same scale and lighting as the replacement."),
        ("02_sculpted_oblique", "REPLACEMENT / SHALLOW BONE RELIEF", "6.2 mm maximum thickness; original 3 mm back, screw seats, and eye bezel retained."),
        ("03_sculpted_front", "FRONT / UNCHANGED HOLES AND OUTLINE", "Raised forehead, brow, cheeks, teeth and jaw; no changes behind the mounting plane."),
        ("04_sculpted_raking", "LOW ANGLE / RELIEF DEPTH", "Only 3.2 mm of extra projection, with recessed access to the existing M2 screws."),
        ("05_assembled", "FITTED TO THE EXISTING CAULDRON", "Original cauldron and HalloWing carrier meshes; reference eye and hardware shown."),
        ("06_core_one_bed", "CORE ONE+ / FACEPLATE-ONLY JOB", "Print flat back down, sculpture up. Existing cauldron and carrier do not need reprinting."),
    )
    records = []
    for name, title, detail in views:
        plot = setup_plot()
        if name == "05_assembled":
            for part in ("bucket_black", "carrier_black", "guard_black"):
                add_solid(plot, load_part(part), BLACK)
            add_solid(plot, polydata(mesh_in_assembly(sculpted)), GLOW)
            electronics(plot)
            battery(plot)
            screw_heads(plot)
            camera, target, scale, up = (310, -470, 290), (0, 0, 102), 146, (0, 0, 1)
        elif name == "06_core_one_bed":
            add_core_one_bed(plot)
            placed = trimesh.load(OUTPUT / "skull_sculpted.3mf", force="scene").to_geometry()
            add_solid(plot, polydata(placed), GLOW)
            for light in plot.renderer.lights:
                light.focal_point = (125, 110, 0)
            camera, target, scale, up = (470, -410, 490), (125, 110, 55), 205, (0, 0, 1)
        else:
            selected = original if name == "01_original_oblique" else sculpted
            actor = add_solid(plot, polydata(selected), GLOW)
            actor.prop.ambient = 0.20
            actor.prop.diffuse = 0.85
            actor.prop.specular = 0.10
            for light, position, intensity in zip(plot.renderer.lights,
                    ((-180, -50, 105), (150, 80, 230), (0, 200, 80)), (0.95, 0.35, 0.20), strict=True):
                light.position = position
                light.focal_point = (0, -15, 2)
                light.intensity = intensity
            camera, target, scale, up = (150, -240, 290), (0, -16, 2), 90, (0, 0, 1)
            if name == "03_sculpted_front":
                camera, up = (0, -16, 350), (0, 1, 0)
            if name == "04_sculpted_raking":
                camera, scale = (80, -260, 100), 76
        plot.camera_position = [camera, target, up]
        plot.camera.parallel_scale = scale
        path = RENDERS / (name + ".png")
        plot.show(screenshot=str(path), auto_close=True)
        caption(path, title, detail)
        pixels = np.asarray(Image.open(path))[160:1120, 160:1400]
        assert np.std(pixels) > 14
        records.append({"image": path.name, "camera": camera, "target": target, "nonblank": True})
        print(f"Rendered {path.name}", flush=True)
    comparison = Image.new("RGB", (1560, 640), BACKGROUND)
    for index, name in enumerate(("01_original_oblique", "02_sculpted_oblique")):
        image = Image.open(RENDERS / (name + ".png")).convert("RGB").resize((780, 640), Image.Resampling.LANCZOS)
        comparison.paste(image, (index * 780, 0))
    comparison.save(RENDERS / "comparison.png")
    overview = Image.new("RGB", (1560, 1280), BACKGROUND)
    for index, name in enumerate(("02_sculpted_oblique", "03_sculpted_front", "04_sculpted_raking", "05_assembled")):
        image = Image.open(RENDERS / (name + ".png")).convert("RGB").resize((780, 640), Image.Resampling.LANCZOS)
        overview.paste(image, ((index % 2) * 780, (index // 2) * 640))
    overview.save(RENDERS / "overview.png")
    (RENDERS / "manifest.json").write_text(json.dumps(records, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--slice", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--slicer", type=Path,
                        default=ROOT / ".cache/prusaslicer-2.9.6/PrusaSlicer-2.9.6/prusa-slicer-console.exe")
    arguments = parser.parse_args()
    if not any((arguments.build, arguments.slice, arguments.render, arguments.all)):
        parser.error("Choose --build, --slice, --render, or --all")
    if arguments.build or arguments.all:
        build_variant()
    if arguments.slice or arguments.all:
        slice_variant(arguments.slicer)
    if arguments.render or arguments.all:
        render_variant()
    verify_baseline()


if __name__ == "__main__":
    main()