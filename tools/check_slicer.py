"""Generate and audit CORE One+ USB jobs for the documented 0.4 HF PLA setup."""

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
PROFILE_VERSION = "2.5.10"
PROFILE_COMMIT = "65c5c8f1e1c3836f306119c49d717759cbc368db"
PROFILE_URL = f"https://raw.githubusercontent.com/prusa3d/PrusaSlicer-settings-prusa-fff/{PROFILE_COMMIT}/PrusaResearch/{PROFILE_VERSION}.ini"
PRINTER_PROFILE = "Prusa CORE One HF0.4 nozzle"
PRINT_PROFILE = "0.20mm STRUCTURAL @COREONE 0.4"
FILAMENT_PROFILE = "Generic PLA @COREONE HF0.4"


def resolve_profile(bundle, kind, name, stack=()):
    section_name = kind + ":" + name
    if section_name in stack:
        raise ValueError("Cyclic official profile inheritance")
    section = dict(bundle[section_name])
    result = {}
    for parent in section.get("inherits", "").split(";"):
        if parent.strip():
            result.update(resolve_profile(bundle, kind, parent.strip(), (*stack, section_name)))
    result.update(section)
    return result


def create_core_one_profiles():
    import urllib.request

    source = ROOT / ".cache" / f"PrusaResearch-{PROFILE_VERSION}.ini"
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        urllib.request.urlretrieve(PROFILE_URL, source)
    bundle = configparser.ConfigParser(interpolation=None, strict=False)
    bundle.read(source, encoding="utf-8")
    printer = resolve_profile(bundle, "printer", PRINTER_PROFILE)
    settings = resolve_profile(bundle, "print", PRINT_PROFILE)
    settings.update(resolve_profile(bundle, "filament", FILAMENT_PROFILE))
    settings.update(printer)
    for key in ("inherits", "alias", "renamed_from", "compatible_printers", "compatible_printers_condition",
                "compatible_prints", "compatible_prints_condition", "default_print_profile",
                "default_filament_profile", "default_sla_material_profile"):
        settings.pop(key, None)
    assert settings["printer_model"] == "COREONE"
    assert settings["nozzle_diameter"] == "0.4" and settings["nozzle_high_flow"] == "1"
    assert settings["bed_shape"] == "0x0,250x0,250x220,0x220"
    settings.update({
        "binary_gcode": "0", "arc_fitting": "disabled", "skirts": "0", "wipe_tower": "0",
        "single_extruder_multi_material": "0", "complete_objects": "0",
        "layer_height": "0.20", "first_layer_height": "0.20", "perimeters": "7",
        "top_solid_layers": "8", "bottom_solid_layers": "10", "fill_density": "15%",
        "fill_pattern": "gyroid", "extrusion_width": "0.45", "perimeter_extrusion_width": "0.45",
        "external_perimeter_extrusion_width": "0.45", "first_layer_extrusion_width": "0.50",
        "support_material_extruder": "1", "support_material_interface_extruder": "1",
        "support_material_style": "organic", "support_material_threshold": "55",
        "support_material_contact_distance": "0.25", "support_material": "0", "brim_width": "0",
        "first_layer_temperature": "220", "temperature": "215",
        "first_layer_bed_temperature": "60", "bed_temperature": "60",
        "chamber_temperature": "20", "chamber_minimal_temperature": "0",
        "filament_type": "PLA", "filament_diameter": "1.75",
        "printer_settings_id": "CORE One+ 0.4 HF - official COREONE",
        "print_settings_id": "Cauldron 0.20mm seven walls",
        "notes": "CORE One+ ONLY / 0.4 mm wear-resistant HIGH-FLOW nozzle / 1.75 mm PLA / 220-215C nozzle / 60C smooth PEI / verify setup before printing",
    })
    output = ROOT / "profiles"
    output.mkdir(exist_ok=True)
    profiles = {}
    for material, density, flow, abrasive in (("black", "1.30", "6", "0"), ("glow", "2.00", "3", "1")):
        profile = settings | {
            "filament_density": density, "filament_max_volumetric_speed": flow,
            "filament_abrasive": abrasive,
            "filament_colour": "#C7E79E" if material == "glow" else "#17191D",
            "filament_settings_id": f"Cauldron {material} PLA 220-215C",
        }
        assert profile["start_gcode"] == printer["start_gcode"]
        assert profile["end_gcode"] == printer["end_gcode"]
        path = output / f"core_one_plus_0.4HF_{material}_PLA.ini"
        path.write_text("\n".join(f"{key} = {value}" for key, value in sorted(profile.items())) + "\n")
        profiles[material] = path
    manifest = {
        "source_url": PROFILE_URL, "bundle_version": PROFILE_VERSION, "source_commit": PROFILE_COMMIT,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "printer_profile": PRINTER_PROFILE, "print_profile": PRINT_PROFILE, "filament_profile": FILAMENT_PROFILE,
        "startup_shutdown_unchanged": True, "nozzle_mm": 0.4, "nozzle_type": "wear-resistant high-flow",
        "firmware_notice": re.search(r"M115 U([^\\]+)", printer["start_gcode"]).group(1),
        "temperatures_c": {"first_layer": 220, "other_layers": 215, "bed": 60, "chamber_target": 20},
        "material_requirement": "1.75 mm PLA rated for these temperatures; glow PLA suitable for a 0.4 mm hardened nozzle",
        "machine_details_confirmed_by_user": False,
        "sheet_assumption": "clean smooth PEI suitable for PLA",
        "slicer_required": "2.9.6",
        "profiles_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in profiles.values()},
    }
    (output / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return profiles


def validate_gcode(contents, material):
    if not contents.startswith("; generated by PrusaSlicer 2.9.6 "):
        raise ValueError("Unexpected G-code generator")
    executable_lines = "\n".join(line.split(";", 1)[0].strip() for line in contents.splitlines())
    required = (
        'M862.3 P "COREONE"',
        "M862.5 P2", 'M862.6 P"Input shaper"', "M115 U6.8.1+16182",
        "G28", "G29 P9", "G29 P1", "G29 A", "M591 R", "M83",
        "M104 S0", "M140 S0", "M141 S0", "M84 X Y E",
    )
    for token in required:
        if token not in executable_lines:
            raise ValueError(f"G-code missing required machine sequence: {token}")
    nozzle_check = f"M862.1 P0.4 A{1 if material == 'glow' else 0} F1"
    if nozzle_check not in executable_lines:
        raise ValueError("Wrong nozzle diameter, high-flow flag, or abrasive-material check")
    coordinates = np.zeros(3)
    minimum = np.full(3, np.inf)
    maximum = np.full(3, -np.inf)
    print_started = False
    layer_count = 0
    extrusion_segments = 0
    feedrate = 0.0
    maximum_flow = 0.0
    hotend_targets, bed_targets = set(), set()
    temperatures = {"hotend": None, "bed": None, "chamber": None}
    number = re.compile(r"([A-Z])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
    for line_number, line in enumerate(contents.splitlines(), start=1):
        if line == ";LAYER_CHANGE":
            print_started = True
            layer_count += 1
        executable = line.split(";", 1)[0].strip()
        if not executable:
            continue
        if "{" in executable or "}" in executable or "[" in executable or "]" in executable:
            raise ValueError(f"Unexpanded G-code expression on line {line_number}")
        command = executable.split()[0]
        parameters = {name: float(value) for name, value in number.findall(executable[len(command):])}
        if command.startswith("T") and command != "T0":
            raise ValueError(f"Unexpected physical tool: {command}")
        if "T" in parameters and parameters["T"] != 0 and command in ("M104", "M109"):
            raise ValueError("Temperature command targets another extruder")
        if command in ("M600", "G20", "G91", "M82", "G2", "G3"):
            raise ValueError(f"Unexpected mode, color change, or unaudited arc: {command}")
        if command == "G92" and any(axis in parameters for axis in "XYZ"):
            raise ValueError("Unexpected model-coordinate reset")
        if command in ("M104", "M109"):
            target = parameters.get("S", parameters.get("R"))
            if target is not None:
                if target not in (0, 100, 170, 215, 220):
                    raise ValueError(f"Unexpected nozzle temperature: {target}")
                hotend_targets.add(target)
                temperatures["hotend"] = target
        if command in ("M140", "M190"):
            target = parameters.get("S", parameters.get("R"))
            if target not in (0, 60):
                raise ValueError(f"Unexpected bed temperature: {target}")
            bed_targets.add(target)
            temperatures["bed"] = target
        if command in ("M141", "M191"):
            target = parameters.get("S", parameters.get("R"))
            if target not in (0, 20):
                raise ValueError(f"Unexpected chamber heating request: {target}")
            temperatures["chamber"] = target
        if command not in ("G0", "G1"):
            continue
        previous = coordinates.copy()
        for index, axis in enumerate("XYZ"):
            if axis in parameters:
                coordinates[index] = parameters[axis]
        feedrate = parameters.get("F", feedrate)
        if not print_started:
            continue
        if any(axis in parameters for axis in "XY"):
            if np.any(coordinates[:2] < -0.001) or np.any(coordinates[:2] > [250.001, 220.001]):
                raise ValueError(f"Model-phase XY move outside bed on line {line_number}")
        if coordinates[2] < 0 or coordinates[2] > 270.001:
            raise ValueError(f"Model-phase Z outside build height on line {line_number}")
        distance = np.linalg.norm(coordinates - previous)
        extrusion = parameters.get("E", 0.0)
        if extrusion > 0 and np.linalg.norm(coordinates[:2] - previous[:2]) > 1e-6:
            if np.any(previous[:2] < 0) or np.any(previous[:2] > [250, 220]):
                raise ValueError("Model extrusion starts outside the bed")
            minimum = np.minimum(minimum, np.minimum(previous, coordinates))
            maximum = np.maximum(maximum, np.maximum(previous, coordinates))
            extrusion_segments += 1
            if distance > 0.4:
                flow = extrusion * np.pi * (1.75 / 2) ** 2 * feedrate / (60 * distance)
                maximum_flow = max(maximum_flow, flow)
    if not layer_count or extrusion_segments < 100:
        raise ValueError("G-code contains no meaningful layered print")
    if not {215, 220}.issubset(hotend_targets) or 60 not in bed_targets:
        raise ValueError("Required PLA temperatures not emitted")
    if any(value != 0 for value in temperatures.values()):
        raise ValueError("G-code leaves a temperature controller active")
    flow_limit = 3.0 if material == "glow" else 6.0
    if maximum_flow > flow_limit + 0.12:
        raise ValueError(f"Extrusion exceeds configured flow limit: {maximum_flow}")
    mass = re.search(r"^; filament used \[g\] = ([0-9.]+)$", contents, flags=re.MULTILINE)
    volume = re.search(r"^; filament used \[cm3\] = ([0-9.]+)$", contents, flags=re.MULTILINE)
    duration = re.search(r"^; estimated printing time \(normal mode\) = (.+)$", contents, flags=re.MULTILINE)
    if not mass or not volume or not duration or float(mass.group(1)) <= 0:
        raise ValueError("Missing single-filament usage/time statistics")
    if "; total filament used for wipe tower [g] = 0.00" not in contents:
        raise ValueError("Unexpected wipe-tower material")
    return {
        "layer_count": layer_count, "extrusion_segments": extrusion_segments,
        "deposition_bounds_mm": [minimum.tolist(), maximum.tolist()],
        "all_model_moves_within_build_volume": True, "single_nozzle_verified": True,
        "startup_checks_and_shutdown_verified": True,
        "maximum_observed_flow_mm3_s": round(maximum_flow, 4),
        "filament_g": float(mass.group(1)), "filament_cm3": float(volume.group(1)),
        "estimated_time": duration.group(1),
        "scope": "Static file audit, not a physical print or a guarantee about unconfirmed hardware/filament",
        "startup_exception": "Official purge/cleaning uses Y=-2.5 outside the print bed before layer 1; retained unchanged",
    }


def verify_gcode_rejections(contents, material="black"):
    mutations = (
        contents.replace(";LAYER_CHANGE", ";LAYER_CHANGE\nT1", 1),
        contents.replace(";LAYER_CHANGE", ";LAYER_CHANGE\nG1 X251 Y100 E1", 1),
        contents.replace("M104 S220", "M104 S280", 1),
        contents.replace("G29 A ; activate mbl", "; missing mesh activation", 1),
    )
    for mutation in mutations:
        assert mutation != contents, "Audit mutation was not applied"
        try:
            validate_gcode(mutation, material)
        except ValueError:
            continue
        raise AssertionError("Unsafe G-code mutation passed the audit")
    return len(mutations)


def invoke(executable, arguments, environment):
    converted = []
    for argument in arguments:
        if isinstance(argument, Path):
            argument = argument.resolve()
            if executable.suffix.lower() == ".exe" and os.name != "nt":
                argument = subprocess.check_output(["wslpath", "-w", str(argument)], text=True).strip()
        converted.append(str(argument))
    process = subprocess.run([str(executable), *converted], env=environment,
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if process.returncode:
        raise RuntimeError(process.stdout + process.stderr)
    return process.stdout + process.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slicer", type=Path,
                        default=ROOT / ".cache/prusaslicer-2.9.6/PrusaSlicer-2.9.6/prusa-slicer-console.exe")
    parser.add_argument("--imports-only", action="store_true")
    arguments = parser.parse_args()
    printed_baseline = json.loads((ROOT / "docs/printed_parts.json").read_text())
    for filename, digest in printed_baseline["files_sha256"].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Already-printed part changed: {filename}")
    previous_report = json.loads((ROOT / "docs/slicer_validation.json").read_text())
    environment = dict(os.environ)
    profiles = create_core_one_profiles()
    cache = ROOT / ".cache/core-one-slice"
    cache.mkdir(parents=True, exist_ok=True)
    version = invoke(arguments.slicer, ["--help"], environment).splitlines()[0]
    if not version.startswith("PrusaSlicer-2.9.6"):
        raise ValueError("Use PrusaSlicer 2.9.6 for the pinned official profile and reproducible USB jobs")
    geometry = json.loads((ROOT / "docs/validation.json").read_text())
    report = {"slicer_version": version,
              "design": geometry["design"],
              "scope": "CORE One+ 0.4 high-flow PLA USB jobs; hardware/material assumptions require confirmation before use",
              "profile_provenance": json.loads((ROOT / "profiles/provenance.json").read_text()),
              "plates": {}}
    jobs = (
        ("01_mount_test_black.3mf", "01_test_BLACK_04HF_PLA.gcode", "black", True, 5),
        ("02_skull_faceplate_glow.3mf", "02_skull_GLOW_04HF_PLA.gcode", "glow", False, 0),
        ("03_carrier_black.3mf", "03_carrier_BLACK_04HF_PLA.gcode", "black", False, 0),
        ("04_guard_black.3mf", "04_guard_BLACK_04HF_PLA.gcode", "black", False, 0),
        ("05_cauldron_black.3mf", "05_cauldron_BLACK_04HF_PLA.gcode", "black", True, 5),
    )
    for filename, gcode_name, material, supports, brim in jobs:
        path = ROOT / "print" / filename
        print(f"Checking {path.name}", flush=True)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != geometry["files_sha256"][filename]:
            raise ValueError(f"Changed plate needs a new CAD validation: {filename}")
        output = invoke(arguments.slicer, ["--info", path], environment)
        values = {}
        object_values = []
        for line in output.splitlines():
            if line.startswith("[") and values:
                object_values.append(values)
                values = {}
            key, separator, value = line.partition(" = ")
            if separator:
                values[key.strip()] = value.strip()
        if values:
            object_values.append(values)
        scene = trimesh.load(path, force="scene")
        expected = np.array(sorted(tuple(geometry.extents) for geometry in scene.geometry.values()))
        actual = np.array(sorted(tuple(float(values[f"size_{axis}"]) for axis in ("x", "y", "z"))
                                 for values in object_values))
        if expected.shape != actual.shape or not np.allclose(expected, actual, atol=0.03):
            raise ValueError(f"Material misalignment in {path.name}: {actual} vs {expected}")
        assert all(values["manifold"] == "yes" for values in object_values)
        native_file = cache / path.name
        common = [
            "--config-compatibility", "disable", "--load", profiles[material],
            "--dont-arrange", "--threads", "4", "--brim-width", str(brim),
            "--support-material" if supports else "--no-support-material",
        ]
        common.extend([
            "--layer-height", "0.10", "--first-layer-height", "0.20",
            "--fill-density", "100%", "--fill-pattern", "rectilinear",
            "--top-solid-layers", "10", "--bottom-solid-layers", "10",
        ] if material == "glow" else [])
        invoke(arguments.slicer, [*common, "--export-3mf", "--output", native_file, path], environment)
        with ZipFile(native_file) as archive:
            config = ET.fromstring(archive.read("Metadata/Slic3r_PE_model.config"))
        assignments = [item.get("value") for item in config.findall("object/volume/metadata[@key='extruder']")]
        expected_assignments = ["1"]
        assert assignments == expected_assignments, f"Wrong native tool assignments: {assignments}"
        result = {"sha256": digest, "material": material,
                  "native_info": output.strip(), "native_volume_extruders": assignments,
                  "dimensions_and_material_alignment_verified": True}
        if not arguments.imports_only and material == "black":
            previous = previous_report["plates"][filename]
            existing = ROOT / previous["gcode_file"]
            assert digest == previous["sha256"]
            assert hashlib.sha256(existing.read_bytes()).hexdigest() == previous["gcode_sha256"]
            audit = validate_gcode(existing.read_text(), material)
            assert audit == previous["gcode_audit"]
            result.update({key: previous[key] for key in ("offline_slice_succeeded", "gcode_audit", "gcode_file",
                                                         "gcode_sha256", "supports", "brim_mm", "profile")})
            result["existing_job_preserved_byte_for_byte"] = True
            print(f"  Preserved existing black job: {audit['filament_g']:.2f} g; audit passed", flush=True)
        elif not arguments.imports_only:
            gcode = cache / gcode_name
            output = invoke(arguments.slicer, [*common, "--export-gcode", "--output", gcode, path], environment)
            (cache / (path.stem + ".log")).write_text(output)
            generated = gcode.read_text()
            contents = "\n".join(line.rstrip(" \t") for line in generated.splitlines()) + "\n"
            assert [line.split(";", 1)[0].strip() for line in generated.splitlines()] == [
                line.split(";", 1)[0].strip() for line in contents.splitlines()
            ], "Formatting changed executable G-code"
            gcode.write_text(contents)
            audit = validate_gcode(contents, material)
            assert audit["layer_count"] >= 60
            assert abs(audit["deposition_bounds_mm"][1][2] - geometry["parts"]["bucket_glow"]["bounds_mm"][1][2]) <= 0.11
            assert not re.search(r"^;TYPE:Support", contents, flags=re.MULTILINE)
            report["unsafe_mutations_rejected"] = verify_gcode_rejections(contents, material)
            result.update({"offline_slice_succeeded": True, "gcode_audit": audit,
                           "gcode_file": "usb/COREONE_04HF_PLA/" + gcode_name,
                           "gcode_sha256": hashlib.sha256(gcode.read_bytes()).hexdigest(),
                           "supports": supports, "brim_mm": brim,
                           "profile": str(profiles[material].relative_to(ROOT)),
                           "overrides": {"layer_height_mm": 0.10, "first_layer_mm": 0.20,
                                         "infill_percent": 100, "fill_pattern": "rectilinear",
                                         "top_bottom_layers": 10, "supports": False, "brim_mm": 0},
                           "postprocessing": "Trailing whitespace removed; executable commands unchanged"})
            print(f"  {audit['filament_g']:.2f} g {material}, {audit['estimated_time']}; G-code audit passed", flush=True)
        report["plates"][path.name] = result
    if not arguments.imports_only:
        totals = {material: round(sum(result["gcode_audit"]["filament_g"] for result in report["plates"].values()
                                      if result["material"] == material), 2) for material in ("black", "glow")}
        assert all(mass < 1000 for mass in totals.values()), "Sliced filament budget exceeded"
        report["all_plates_estimated_g"] = totals
        target = ROOT / "usb/COREONE_04HF_PLA"
        target.mkdir(parents=True, exist_ok=True)
        for _, gcode_name, material, _, _ in jobs:
            if material == "glow":
                shutil.copyfile(cache / gcode_name, target / gcode_name)
    for filename, digest in printed_baseline["files_sha256"].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == digest, filename
    destination = ROOT / "docs" / ("slicer_import_validation.json" if arguments.imports_only else "slicer_validation.json")
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verified_plates": len(report["plates"]),
                      "all_plates_estimated_g": report.get("all_plates_estimated_g"),
                      "report": str(destination.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()