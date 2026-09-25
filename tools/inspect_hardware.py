"""Extract mechanical facts from Adafruit's Eagle XML without guessing from photos."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def world_point(element, horizontal, vertical):
    rotation = element.get("rot", "R0")
    if "M" in rotation:
        horizontal = -horizontal
    angle = math.radians(float(rotation.split("R")[-1]))
    return (
        float(element.get("x", "0")) + horizontal * math.cos(angle) - vertical * math.sin(angle),
        float(element.get("y", "0")) + horizontal * math.sin(angle) + vertical * math.cos(angle),
    )


def inspect_board(path: Path) -> dict:
    board = ET.parse(path).getroot().find("drawing/board")
    if board is None:
        raise ValueError("Expected an Eagle board")
    holes = [
        {key: float(hole.attrib[key]) for key in ("x", "y", "drill")}
        for hole in board.findall("plain/hole")
    ]
    elements = [
        dict(element.attrib)
        for element in board.findall("elements/element")
        if any(
            term in (element.get("package", "") + element.get("value", "")).upper()
            for term in ("TFT", "LCD", "MOUNT", "USB", "JST", "SWITCH")
        )
    ]
    packages = {
        (library.get("name"), package.get("name")): package
        for library in board.findall("libraries/library")
        for package in library.findall("packages/package")
    }
    plated = []
    outline = []
    for element in board.findall("elements/element"):
        package = packages[(element.get("library"), element.get("package"))]
        if element.get("package") == "MOUNTINGHOLE_2.5_PLATED":
            for pad in package.findall("pad"):
                horizontal, vertical = world_point(element, float(pad.get("x")), float(pad.get("y")))
                plated.append({"x": horizontal, "y": vertical, "drill": float(pad.get("drill"))})
        if element.get("package") == "HALLOWING_FRONT":
            for wire in package.findall("wire"):
                if wire.get("layer") != "20":
                    continue
                start = world_point(element, float(wire.get("x1")), float(wire.get("y1")))
                end = world_point(element, float(wire.get("x2")), float(wire.get("y2")))
                outline.append({"start": start, "end": end, "curve_degrees": float(wire.get("curve", "0"))})
    if not holes:
        raise ValueError("No plain mounting holes; inspect package-local holes instead")
    lens_holes = sorted([hole for hole in holes + plated if 2.4 < hole["drill"] < 2.7],
                        key=lambda hole: (hole["y"], hole["x"]))
    assert len(lens_holes) == 4
    assert math.isclose(lens_holes[1]["x"] - lens_holes[0]["x"], 17.78, abs_tol=0.001)
    assert math.isclose(lens_holes[2]["y"] - lens_holes[0]["y"], 45.72, abs_tol=0.001)
    assert len(outline) == 24
    return {
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "units": "mm",
        "plain_holes": holes,
        "lens_mounting_holes": lens_holes,
        "mechanical_elements": elements,
        "outline_segments": outline,
    }


def inspect_lens(path: Path) -> dict:
    import pymupdf

    document = pymupdf.open(path)
    subpaths = []
    points = []
    first = None
    for item in document[0].get_drawings()[0]["items"]:
        if first is None:
            first = item[1]
        points.extend(item[1:])
        if abs(item[-1] - first) < 1e-4:
            subpaths.append((min(point.x for point in points), min(point.y for point in points),
                             max(point.x for point in points), max(point.y for point in points)))
            points, first = [], None
    conversion = 25.4 / 72
    holes = [bounds for bounds in subpaths if (bounds[2] - bounds[0]) * conversion < 4]
    aperture = [bounds for bounds in subpaths if 30 < (bounds[2] - bounds[0]) * conversion < 40][0]
    hole_centers = [((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2) for bounds in holes]
    center_y = (aperture[1] + aperture[3]) / 2
    upper_hole_y = min(center[1] for center in hole_centers)
    center_eagle = 27.559 - (center_y - upper_hole_y) * conversion
    width = (max(center[0] for center in hole_centers) - min(center[0] for center in hole_centers)) * conversion
    height = (max(center[1] for center in hole_centers) - upper_hole_y) * conversion
    assert len(holes) == 4
    assert math.isclose(width, 17.78, abs_tol=0.01)
    assert math.isclose(height, 45.72, abs_tol=0.01)
    assert math.isclose(center_eagle, 3.082925, abs_tol=0.001)
    return {"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "hole_pitch_mm": [width, height], "optical_center_eagle_y_mm": center_eagle,
            "historical_drawing_aperture_mm": (aperture[2] - aperture[0]) * conversion,
            "note": "Published drawing is historical; retain the purchased acrylic and verify its physical revision."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("--lens", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = {"board": inspect_board(arguments.board)}
    if arguments.lens:
        result["lens_drawing"] = inspect_lens(arguments.lens)
    content = json.dumps(result, indent=2) + "\n"
    if arguments.output:
        arguments.output.write_text(content)
        print(f"Verified four 17.78 x 45.72 mm mounting holes; wrote {arguments.output}")
    else:
        print(content)