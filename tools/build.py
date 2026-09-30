"""Export single-material CORE One+ plates, manufacturing meshes, and STEP solids."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import cadquery as cq
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from design.bucket import (
    BOARD_HOLES,
    BUCKET_FASTENERS,
    DIMENSIONS,
    GUARD_FASTENERS,
    balance_report,
    block,
    bucket_black,
    cauldron_body,
    cauldron_radius_profile,
    carrier,
    coupon_black,
    coupon_glow,
    cylinder_y,
    guard,
    mass_properties,
    print_parts,
    skull_glow,
    solid_volume,
    verify_faceplate,
    verify_mount,
)

CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", CORE)
COLORS = {"black": "#17191D", "glow": "#C7E79E"}
BUILD_VOLUME = np.array([250.0, 220.0, 270.0])


def file_sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_printed_parts():
    baseline = json.loads((ROOT / "docs/printed_parts.json").read_text())
    for filename, digest in baseline["files_sha256"].items():
        if file_sha256(ROOT / filename) != digest:
            raise ValueError(f"Existing printed-part file changed: {filename}")
    assert DIMENSIONS.rope_axis_y == baseline["rope_axis_y_mm"]
    return baseline


def existing_part_compatibility():
    collisions = {}
    for name, shape in (("bucket_black", bucket_black()), ("carrier_black", carrier()), ("guard_black", guard())):
        saved = cq.importers.importStep(str(ROOT / "cad" / f"{name}.step")).val()
        if name != "bucket_black":
            back = DIMENSIONS.carrier_back if name == "carrier_black" else DIMENSIONS.guard_back_inner + DIMENSIONS.guard_thickness
            saved = saved.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, back, DIMENSIONS.eye_z))
        overlap = solid_volume(saved.intersect(skull_glow()))
        assert overlap < 1e-5, f"Faceplate collides with saved {name}"
        assert abs(solid_volume(shape) - solid_volume(saved)) / solid_volume(saved) < 1e-6
        assert all(abs(getattr(shape.BoundingBox(), axis) - getattr(saved.BoundingBox(), axis)) < 1e-5
                   for axis in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"))
        collisions[name] = overlap
    return collisions


def mesh_from_shape(shape):
    vertices, triangles = shape.tessellate(0.002, 0.03)
    mesh = trimesh.Trimesh(
        vertices=np.array([vertex.toTuple() for vertex in vertices]),
        faces=np.array(triangles),
        process=True,
    )
    mesh.merge_vertices(digits_vertex=6)
    mesh.remove_unreferenced_vertices()
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("Invalid manufacturing mesh: not closed, consistently wound, and positive")
    if abs(mesh.volume - solid_volume(shape)) / solid_volume(shape) > 0.003:
        raise ValueError("Mesh tessellation lost more than 0.3% of the CAD volume")
    _, center = mass_properties(shape)
    if np.max(np.abs(mesh.center_mass - np.asarray(center))) > 0.15:
        raise ValueError("Mesh center of mass differs from CAD by more than 0.15 mm")
    return mesh


def xml_bytes(element):
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def write_3mf(path, objects, meshes):
    model = ET.Element(f"{{{CORE}}}model", unit="millimeter", attrib={"xml:lang": "en-US"})
    ET.SubElement(model, "metadata", name="Title").text = path.stem
    ET.SubElement(model, "metadata", name="Designer").text = "Cyclops cauldron"
    ET.SubElement(model, "metadata", name="Description").text = (
        "Prusa CORE One+ single-nozzle geometry. One filament per job, extruder 1 only. "
        "The sculpted glow skull prints flat-back-down and attaches with the existing four M2 screws."
    )
    resources = ET.SubElement(model, "resources")
    materials = ET.SubElement(resources, "basematerials", id="100")
    for color, value in COLORS.items():
        ET.SubElement(materials, "base", name=color, displaycolor=value + "FF")
    build = ET.SubElement(model, "build")
    config = ET.Element("config")
    for object_id, (label, names, placement) in enumerate(objects, start=1):
        object_element = ET.SubElement(resources, "object", id=str(object_id), type="model", name=label)
        mesh_element = ET.SubElement(object_element, "mesh")
        vertices = ET.SubElement(mesh_element, "vertices")
        triangles = ET.SubElement(mesh_element, "triangles")
        settings = ET.SubElement(config, "object", id=str(object_id), instances_count="1")
        ET.SubElement(settings, "metadata", type="object", key="name", value=label)
        vertex_offset = 0
        triangle_offset = 0
        for name in names:
            mesh = meshes[name]
            material = 1 if name.endswith("glow") else 0
            for vertex in mesh.vertices + np.asarray(placement):
                ET.SubElement(vertices, "vertex", x=f"{vertex[0]:.6f}",
                              y=f"{vertex[1]:.6f}", z=f"{vertex[2]:.6f}")
            for face in mesh.faces:
                ET.SubElement(triangles, "triangle", v1=str(int(face[0]) + vertex_offset),
                              v2=str(int(face[1]) + vertex_offset),
                              v3=str(int(face[2]) + vertex_offset), pid="100", p1=str(material))
            volume = ET.SubElement(settings, "volume", firstid=str(triangle_offset),
                                   lastid=str(triangle_offset + len(mesh.faces) - 1))
            ET.SubElement(volume, "metadata", type="volume", key="name", value=name)
            ET.SubElement(volume, "metadata", type="volume", key="volume_type", value="ModelPart")
            ET.SubElement(volume, "metadata", type="volume", key="extruder", value="1")
            vertex_offset += len(mesh.vertices)
            triangle_offset += len(mesh.faces)
        ET.SubElement(build, "item", objectid=str(object_id), transform="1 0 0 0 1 0 0 0 1 0 0 0")
    types = ET.Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
    ET.SubElement(types, "Default", Extension="rels",
                  ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(types, "Default", Extension="model",
                  ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml")
    ET.SubElement(types, "Default", Extension="config", ContentType="application/xml")
    relationships = ET.Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
    ET.SubElement(relationships, "Relationship", Id="rel0", Target="/3D/3dmodel.model",
                  Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel")
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", xml_bytes(types))
        archive.writestr("_rels/.rels", xml_bytes(relationships))
        archive.writestr("3D/3dmodel.model", xml_bytes(model))
        archive.writestr("Metadata/Slic3r_PE_model.config", xml_bytes(config))


def check_plate(path, meshes, objects):
    placed_bounds = []
    for label, names, translation in objects:
        bounds = np.stack([meshes[name].bounds for name in names])
        minimum = bounds[:, 0].min(axis=0) + translation
        maximum = bounds[:, 1].max(axis=0) + translation
        if np.any(minimum < -0.001) or np.any(maximum > BUILD_VOLUME + 0.001):
            raise ValueError(f"{label} exceeds the CORE One+ build volume")
        if np.any(minimum[:2] < 5) or np.any(maximum[:2] > BUILD_VOLUME[:2] - 5):
            raise ValueError(f"{label} has less than 5 mm of XY bed allowance")
        assert all(name.endswith("glow") == names[0].endswith("glow") for name in names)
        for other_minimum, other_maximum in placed_bounds:
            overlap = np.minimum(maximum[:2], other_maximum[:2]) - np.maximum(minimum[:2], other_minimum[:2])
            if np.all(overlap > 0):
                raise ValueError(f"{label} overlaps another object on its plate")
        placed_bounds.append((minimum, maximum))
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt 3MF zip member")
        model = ET.fromstring(archive.read("3D/3dmodel.model"))
        settings = ET.fromstring(archive.read("Metadata/Slic3r_PE_model.config"))
        assert model.get("unit") == "millimeter"
        assert len(model.findall(f"{{{CORE}}}build/{{{CORE}}}item")) == len(objects)
        for object_settings, (_, names, _) in zip(settings.findall("object"), objects, strict=True):
            for volume, name in zip(object_settings.findall("volume"), names, strict=True):
                assignment = volume.find("metadata[@key='extruder']")
                assert assignment is not None
                assert assignment.get("value") == "1"
    loaded = trimesh.load(path, force="scene")
    reimported = sum(abs(geometry.volume) for geometry in loaded.geometry.values())
    expected = sum(meshes[name].volume for _, names, _ in objects for name in names)
    if abs(reimported - expected) / expected > 1e-5:
        raise ValueError("3MF round trip changed model volume")
    material = "glow" if objects[0][1][0].endswith("glow") else "black"
    return {"objects": len(objects), "build_volume_mm": BUILD_VOLUME.tolist(),
            "minimum_xy_bed_allowance_mm": 5, "material": material,
            "extruder": 1, "round_trip_volume_verified": True}


def geometry_checks():
    verify_printed_parts()
    verify_mount()
    verify_faceplate()
    existing_part_compatibility()
    black = bucket_black()
    glow = skull_glow()
    for first, second, label in ((black, glow, "materials"), (black, carrier(), "carrier"),
                                  (black, guard(), "guard"), (carrier(), guard(), "pod")):
        assert solid_volume(first.intersect(second)) < 1e-5, f"Collision: {label}"
    assert len(black.Solids()) == len(glow.Solids()) == 1, "Each separately printed part must be connected"
    axis = cylinder_y(DIMENSIONS.eye_bore / 2 - 0.15, DIMENSIONS.front - 8, 20, 0, DIMENSIONS.eye_z)
    assert solid_volume(black.fuse(glow).intersect(axis)) < 1e-5, "Eye opening blocked"
    common = block(104, 12, 98, (0, DIMENSIONS.front, DIMENSIONS.eye_z))
    for full, coupon in ((black, coupon_black()), (glow, coupon_glow())):
        full_section = full.intersect(common)
        test_section = coupon.intersect(common)
        assert not full_section.cut(test_section).Solids(), "Coupon is missing part of the cauldron section"
        assert not test_section.cut(full_section).Solids(), "Coupon adds material inside the cauldron section"
    for part in (glow, carrier(), guard()):
        assert solid_volume(coupon_black().intersect(part)) < 1e-5, "Coupon foot obstructs the reusable assembly"
    for horizontal, vertical in BUCKET_FASTENERS:
        passage = cylinder_y(1.0, DIMENSIONS.front - 1, 38, horizontal, DIMENSIONS.eye_z + vertical)
        assert solid_volume(black.intersect(passage)) + solid_volume(carrier().intersect(passage)) < 1e-5
    for horizontal, vertical in GUARD_FASTENERS:
        passage = cylinder_y(1.0, DIMENSIONS.carrier_front - 0.1, 18, horizontal, DIMENSIONS.eye_z + vertical)
        assert solid_volume(carrier().intersect(passage)) + solid_volume(guard().intersect(passage)) < 1e-5
    battery_envelope = block(DIMENSIONS.battery_pocket_width - 0.2, DIMENSIONS.battery_pocket_depth - 0.2,
                             DIMENSIONS.battery_pocket_height - 0.2,
                             (0, DIMENSIONS.guard_back_inner - DIMENSIONS.battery_pocket_depth / 2, 80))
    assert solid_volume(guard().intersect(battery_envelope)) < 1e-5, "Battery bay obstructed"
    _, plain_center = mass_properties(cauldron_body())
    assert abs(plain_center[0]) < 0.05, "Symmetric shell has a spurious lateral mass moment"
    lower_slopes = cauldron_radius_profile().derivative()(np.linspace(0, 52, 521))
    assert np.max(lower_slopes) < np.tan(np.radians(35)), "Lower bowl needs broad support below 55 degrees"
    shoulder_slopes = cauldron_radius_profile().derivative()(np.linspace(52, DIMENSIONS.height - 6, 1000))
    assert -np.min(shoulder_slopes) < np.tan(np.radians(35)), "Shoulder needs broad interior support below 55 degrees"
    balance = balance_report()
    for horizontal, depth, height in balance["anchor_centers_mm"]:
        direction = 1 if horizontal > 0 else -1
        axis = cq.Vector(direction, 0, 0)
        inner_x = DIMENSIONS.rope_anchor_inner_x
        passage = cq.Solid.makeCylinder(6.25, 25, cq.Vector(direction * (inner_x - 8), depth, height), axis)
        assert solid_volume(black.intersect(passage)) < 1e-5, "Balanced rope passage obstructed"
        outer_ring = cq.Solid.makeCylinder(12, 9, cq.Vector(direction * (inner_x + 0.5), depth, height), axis)
        inner_ring = cq.Solid.makeCylinder(8, 9, cq.Vector(direction * (inner_x + 0.5), depth, height), axis)
        bearing_ring = outer_ring.cut(inner_ring)
        assert solid_volume(bearing_ring.cut(black)) < 1e-3, "Rope lug has a broken load-bearing annulus"
    return {"no_material_or_assembly_collisions": True, "coupon_matches_bucket": True,
            "eye_and_fastener_passages_clear": True, "battery_clearance_verified": True,
            "separate_screw_mounted_faceplate_verified": True,
            "balanced_rope_passages_and_bearing_rings_verified": True,
            "printed_black_files_and_interfaces_preserved": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "print")
    arguments = parser.parse_args()
    output = arguments.output
    output.mkdir(parents=True, exist_ok=True)
    (ROOT / "cad").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)
    checks = geometry_checks()
    shapes = print_parts()
    meshes = {}
    part_report = {}
    for name, shape in shapes.items():
        assert shape.isValid()
        if name.endswith("black"):
            assert len(shape.Solids()) == 1, f"Disconnected solid: {name}"
            print(f"Preserving existing {name}", flush=True)
            source = ROOT / "print" / f"{name}.stl"
            mesh = trimesh.load_mesh(source)
            assert mesh.is_watertight and mesh.is_winding_consistent
            assert abs(mesh.volume - solid_volume(shape)) / solid_volume(shape) < 0.003
            if output.resolve() != source.parent.resolve():
                (output / source.name).write_bytes(source.read_bytes())
        else:
            print(f"Exporting sculpted {name}", flush=True)
            mesh = mesh_from_shape(shape)
            mesh.export(output / f"{name}.stl")
            step_path = ROOT / "cad" / f"{name}.step"
            cq.exporters.export(shape, str(step_path))
            step_path.write_text("\n".join(line.rstrip(" \t") for line in step_path.read_text().splitlines()) + "\n")
        meshes[name] = mesh
        material = "glow" if name.endswith("glow") else "black"
        density = 2.0 if material == "glow" else 1.30
        part_report[name] = {
            "material": material, "cad_volume_cm3": round(solid_volume(shape) / 1000, 4),
            "solid_mass_upper_g": round(solid_volume(shape) * density / 1000, 2),
            "bounds_mm": np.round(mesh.bounds, 4).tolist(),
            "cad_center_of_mass_mm": mass_properties(shape)[1],
            "triangles": len(mesh.faces), "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "mesh_components": len(mesh.split(only_watertight=False)),
        }
    plates = {}
    for filename, label, name in (
        ("01_mount_test_black.3mf", "Black mounting test", "test_black"),
        ("02_skull_faceplate_glow.3mf", "Sculpted glow skull - existing M2 mount", "bucket_glow"),
        ("03_carrier_black.3mf", "HalloWing carrier", "carrier_black"),
        ("04_guard_black.3mf", "Battery cradle and candy guard", "guard_black"),
        ("05_cauldron_black.3mf", "Single-material black cauldron", "bucket_black"),
    ):
        center = meshes[name].bounds.mean(axis=0)
        placement = [125.0 - center[0], 110.0 - center[1], 0.0]
        plates[filename] = [(label, [name], placement)]
    plate_report = {}
    for filename, objects in plates.items():
        path = output / filename
        if objects[0][1][0].endswith("black"):
            original = ROOT / "print" / filename
            if path.resolve() != original.resolve():
                path.write_bytes(original.read_bytes())
        else:
            write_3mf(path, objects, meshes)
        plate_report[filename] = check_plate(path, meshes, objects)
    budgets = {}
    for material, reserve in (("black", 125), ("glow", 50)):
        mass = sum(part["solid_mass_upper_g"] for part in part_report.values() if part["material"] == material)
        budgets[material] = {
            "density_upper_g_cm3": 1.30 if material == "black" else 2.0,
            "solid_parts_including_test_g": round(mass, 2),
            "reserved_for_support_brim_priming_g": reserve,
            "total_budget_g": round(mass + reserve, 2),
            "limit_g": 1000, "within_limit": mass + reserve <= 1000,
        }
        assert budgets[material]["within_limit"], f"{material} filament budget exceeded"
    assembly = cq.Assembly(name="Cyclops_cauldron_assembly")
    for name, shape, color in (
        ("Bucket_black", bucket_black(), cq.Color(0.07, 0.08, 0.09)),
        ("Skull_glow", skull_glow(), cq.Color(0.73, 0.90, 0.53)),
        ("Carrier", carrier(), cq.Color(0.16, 0.18, 0.20)),
        ("Candy_guard", guard(), cq.Color(0.12, 0.14, 0.16)),
    ):
        assembly.add(shape, name=name, color=color)
    assembly_path = ROOT / "cad" / "assembled_bucket.step"
    assembly.export(str(assembly_path))
    assembly_path.write_text("\n".join(line.rstrip(" \t") for line in assembly_path.read_text().splitlines()) + "\n")
    report = {
        "design": "Cyclops cauldron, revision 6, prominent sculpted faceplate", "units": "mm",
        "parameters": asdict(DIMENSIONS), "board_holes_relative_to_eye_mm": BOARD_HOLES,
        "checks": checks, "parts": part_report, "plates": plate_report,
        "material_budgets": budgets,
        "balance": balance_report(),
        "faceplate_compatibility": verify_faceplate(),
        "existing_step_collisions_mm3": existing_part_compatibility(),
        "printed_part_baseline": "docs/printed_parts.json",
        "limitations": [
            "No physical fit or rope-load test has been performed.",
            "Mass bounds assume black density <=1.30 and glow <=2.00 g/cm3.",
            "Printing overhead must remain within the stated reserves; verify slicer totals.",
            "Each geometry 3MF is one material. USB G-code is only for the explicitly documented nozzle and PLA setup.",
            "PCB coordinates come from Adafruit's published older Eagle revision; test your hardware.",
        ],
    }
    previous_report = ROOT / "docs" / "validation.json"
    if previous_report.exists():
        previous_hashes = json.loads(previous_report.read_text()).get("files_sha256", {})
        for filename in ("01_full_bucket_dual.3mf", "02_mount_test_dual.3mf", "03_electronics_black.3mf", "test_glow.stl"):
            stale = output / filename
            if stale.exists():
                if hashlib.sha256(stale.read_bytes()).hexdigest() != previous_hashes.get(filename):
                    raise ValueError(f"Refusing to remove modified obsolete export: {stale}")
                stale.unlink()
    stale_test_step = ROOT / "cad" / "test_glow.step"
    if stale_test_step.exists():
        stale_test_step.unlink()
    report["files_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.iterdir()) if path.suffix in (".stl", ".3mf")
    }
    verify_printed_parts()
    (ROOT / "docs" / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"checks": checks, "material_budgets": budgets}, indent=2))


if __name__ == "__main__":
    main()