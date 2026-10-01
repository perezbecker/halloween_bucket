"""Render numbered assembly cards from the validated manufacturing meshes."""

from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyvista as pv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from design.bucket import BOARD_HOLES, BUCKET_FASTENERS, DIMENSIONS, FACEPLATE_FASTENERS, GUARD_FASTENERS
from tools.render import (
    BACKGROUND, BLACK, GLOW, add_box, add_cylinder, add_ground, add_solid,
    electronics, file_sha256, load_part, screw_heads, setup_plot,
)

OUTPUT = ROOT / "renders" / "assembly"
AMBER = "#AD681B"
BLUE = "#23799D"
TEAL = "#287E72"
PURPLE = "#795597"
STEPS = {
    "01_skull_to_wall": ("01 / ATTACH THE SCULPTED SKULL", "Fit-test steps 2-3 / outside of the wall",
                         (205, -370, 265), (0, -94, 118), 108),
    "02_lens_and_carrier": ("02 / BUILD THE LENS AND PCB MODULE", "Fit-test steps 4-5 / USB connector upward",
                           (235, -260, 230), (0, -35, 125), 92),
    "03_carrier_to_wall": ("03 / MOUNT AND ALIGN THE CARRIER", "Fit-test steps 6-8 / view from the candy side",
                          (310, 170, 240), (0, -64, 123), 113),
    "04_battery_and_strap": ("04 / PAD AND STRAP THE BATTERY", "Fit-test step 9 / guard open toward you",
                            (180, -310, 230), (0, -63, 110), 84),
    "05_close_guard": ("05 / FIT THE REMOVABLE GUARD", "Fit-test steps 10-11 / view from the candy side",
                       (360, 320, 250), (0, -5, 119), 116),
    "06_rope_and_final_checks": ("06 / TRANSFER, TIE AND HANG-TEST", "Only after the small mounting test passes",
                                (330, -480, 390), (0, 0, 150), 193),
}


def washer(plot, horizontal, depth, vertical, thickness, diameter, color):
    ring = pv.Disc(center=(horizontal, depth - thickness / 2, vertical),
                   inner=diameter / 2 + 0.15, outer=2.6 if diameter == 2 else 3.0,
                   normal=(0, 1, 0), r_res=1, c_res=64)
    add_solid(plot, ring.extrude((0, thickness, 0), capping=True), color)


def fastener(plot, horizontal, vertical, seat, length, color, diameter=2.0, reverse=False):
    direction = -1 if reverse else 1
    thickness = DIMENSIONS.rear_pcb_washer if diameter == 2.5 else 0.5
    under_head = seat - direction * thickness
    washer(plot, horizontal, seat - direction * thickness / 2, vertical,
           thickness, diameter, "#E7E4CE" if diameter == 2.5 else color)
    add_cylinder(plot, diameter / 2, length,
                 (horizontal, under_head + direction * length / 2, vertical), color)
    add_cylinder(plot, diameter, 1.8, (horizontal, under_head - direction * 0.9, vertical), color)


def nut(plot, horizontal, depth, vertical, color):
    ring = pv.Disc(center=(horizontal, depth - 0.8, vertical), inner=1.0, outer=4 / np.sqrt(3),
                   normal=(0, 1, 0), r_res=1, c_res=6)
    add_solid(plot, ring.extrude((0, 1.6, 0), capping=True), color)


def guide_axis(plot, horizontal, vertical, start, end, color):
    plot.add_mesh(pv.Line((horizontal, start, vertical), (horizontal, end, vertical)),
                  color=color, opacity=0.45, line_width=1, lighting=False)


def assembly_scene(name):
    plot = setup_plot()
    plot.window_size = (1160, 960)
    d = DIMENSIONS
    if name == "01_skull_to_wall":
        shift = -22
        seat = d.front - d.faceplate_thickness + shift - 18
        add_solid(plot, load_part("test_black"), BLACK)
        add_solid(plot, load_part("bucket_glow"), GLOW, (0, shift, 0))
        for horizontal, vertical in FACEPLATE_FASTENERS:
            z = d.eye_z + vertical
            fastener(plot, horizontal, z, seat, 10, AMBER)
            nut(plot, horizontal, d.inner_front + 3, z, AMBER)
            guide_axis(plot, horizontal, z, seat - 3, d.inner_front + 5, AMBER)
        for horizontal, vertical in BUCKET_FASTENERS:
            washer(plot, horizontal, d.front + shift - d.faceplate_thickness - 0.2,
                   d.eye_z + vertical, 0.2, 2, BLUE)
        notes = [
            ("4 x M2 x 10 + washers", "Amber screws use the four recessed 3 mm skull seats. Tighten gently, with washers on the glow side.",
             (-30, seat - 2, 165), AMBER),
            ("4 loose M2 nuts", "Nuts go inside the black wall. The skull back sits flat against the wall; do not bend it.",
             (30, d.inner_front + 3, 80), AMBER),
            ("Carrier access, NOT skull fixing", "Blue rings mark the other four openings. Leave them clear for the M2 x 20 carrier screws in card 03.",
             (40, d.front + shift - 3.2, 160), BLUE),
        ]
        caution = "Deburr printed passages with electronics removed. Hold the coupon above the bench: the skull extends below its foot."
    elif name == "02_lens_and_carrier":
        shift = 32
        seat = d.carrier_back + shift + 27
        electronics(plot)
        add_solid(plot, load_part("carrier_black"), BLACK, (0, shift, 0))
        for horizontal, vertical in BOARD_HOLES:
            z = d.eye_z + vertical
            fastener(plot, horizontal, z, seat, d.rear_pcb_screw_length, TEAL, diameter=2.5, reverse=True)
            guide_axis(plot, horizontal, z, d.holder_front - 4, seat + 3, TEAL)
        notes = [
            ("4 x M2.5 x 20, from the rear", "Each screw passes through a 1 mm insulating washer, carrier, printed post and PCB into a stock standoff.",
             (8.89, seat + 2, d.eye_z + BOARD_HOLES[2][1]), TEAL),
            ("12 mm printed rear posts", "Rest the PCB only on these four small post ends. Check the real board holes and rear-component clearance.",
             (-8.89, d.pcb_rear + shift, d.eye_z + BOARD_HOLES[0][1]), TEAL),
            ("HalloWing M0 / USB up", "Do not substitute another board. Keep the display/lens assembly together; do not force or bend the PCB.",
             (-22, d.pcb_rear, d.eye_z + 15), BLUE),
            ("Stock lens kit", "Retain the acrylic, four 6 mm M2.5 standoffs and four front M2.5 x 5 screws. The kit, not the bucket, holds the glass.",
             (8.89, d.pcb_front - 3, d.eye_z + BOARD_HOLES[2][1]), AMBER),
        ]
        caution = "M2 and M2.5 are NOT interchangeable. Check engagement by hand: opposing screw tips must not meet inside the standoffs."
    elif name == "03_carrier_to_wall":
        shift = 32
        seat = d.front - 55
        add_solid(plot, load_part("test_black"), BLACK)
        add_solid(plot, load_part("bucket_glow"), GLOW)
        add_solid(plot, load_part("carrier_black"), BLACK, (0, shift, 0), opacity=0.55)
        electronics(plot, (0, shift, 0))
        for horizontal, vertical in BUCKET_FASTENERS:
            z = d.eye_z + vertical
            fastener(plot, horizontal, z, seat, d.bucket_screw_length, BLUE)
            nut(plot, horizontal, d.bucket_nut_front + shift + d.bucket_nut_thickness / 2, z, BLUE)
            guide_axis(plot, horizontal, z, seat, d.carrier_back + shift + 4, BLUE)
        plot.add_mesh(pv.Arrow(start=(58, d.carrier_back + shift, 115), direction=(0, 0, 1), scale=20),
                      color=BLUE, lighting=False)
        plot.add_mesh(pv.Arrow(start=(58, d.carrier_back + shift, 115), direction=(0, 0, -1), scale=20),
                      color=BLUE, lighting=False)
        notes = [
            ("4 x M2 x 20 + washers", "Use the supplied M2 x 20 carrier. Insert through the skull access openings and black wall. Start all four screws loosely in the metal nuts.",
             (40, seat - 2, 160), BLUE),
            ("4 nuts, deep inside the wells", "Load from the REAR and seat at the bottom, 15.9 mm in. Carrier is ghosted to show the nuts. Use tweezers or a blunt tool, never force.",
             (-40, d.bucket_nut_front + shift + 0.8, 160), BLUE),
            ("Adjust vertically, then tighten", "The slots allow +/-2 mm, not the exploded spacing shown. Center the glass with clearance all around; do not pull it through a tight opening.",
             (58, d.carrier_back + shift, 115), BLUE),
            ("Same posts and lens position", "The nuts move forward, not the PCB. Each nut bears on 13 mm of post; a 20 mm screw projects 1.9 mm past a 1.6 mm nut with a 0.5 mm washer.",
             (40, d.bucket_nut_front + shift, 90), TEAL),
        ]
        caution = "Power-test centering, focus and oblique viewing before fitting the guard. Remove power again before continuing assembly."
    elif name == "04_battery_and_strap":
        add_solid(plot, load_part("guard_black"), BLACK)
        center_y = d.guard_back_inner - 1 - d.battery_thickness / 2
        add_box(plot, (31, 1, 40), (0, d.guard_back_inner - 0.5, 80), "#A3BDCC")
        add_box(plot, (d.battery_width, d.battery_thickness, d.battery_height), (0, center_y, 78), "#AFB6BE")
        add_box(plot, (25, 0.2, 23), (0, center_y - d.battery_thickness / 2 - 0.1, 77), "#EAEEE9")
        add_box(plot, (29, 4.9, 4), (0, center_y, 94), "#D7A725")
        strap_front = center_y - d.battery_thickness / 2 - 1.5
        strap_back = d.guard_back_inner + d.guard_thickness + 1
        add_box(plot, (44, 1, 9), (0, strap_front, 80), "#736957")
        add_box(plot, (44, 1, 9), (0, strap_back, 80), "#736957")
        for horizontal in (-21.5, 21.5):
            add_box(plot, (1, strap_back - strap_front, 9),
                    (horizontal, (strap_front + strap_back) / 2, 80), "#736957")
        for horizontal, color in ((-1.1, "#A5413A"), (1.1, "#26292B")):
            points = [(horizontal, center_y, 96), (horizontal + 8, center_y - 1, 108),
                      (horizontal + 23, center_y - 2, 120)]
            plot.add_mesh(pv.Spline(points, 40).tube(radius=0.55), color=color)
        notes = [
            ("Soft insulating pad", "Place an approximately 1 mm pad between the pouch and guard back. The actual battery, including its taped end, must fit loosely.",
             (14, d.guard_back_inner - 1, 99), BLUE),
            ("500 mAh LiPo reference", "Nominal pouch: 29 x 36 x 4.75 mm. Printed bay: 33 x 42 x 8.5 mm. Do not force a larger or swollen battery.",
             (-10, center_y - 2.5, 91), AMBER),
            ("Soft 8-10 mm strap", "Thread both side slots. Retain without squeezing the pouch; the strap loop shown is schematic, not a tension setting.",
             (-21.5, strap_front, 80), TEAL),
            ("Lead exits at the top", "Route toward the board with slack. Keep the lead out of screw paths, guard edges and the USB opening.",
             (23, center_y - 2, 120), AMBER),
        ]
        caution = "Fit the battery with the guard lying flat. Never clamp, pierce or overtighten the pouch; do not use a damaged or hot LiPo."
    elif name == "05_close_guard":
        shift = 100
        seat = d.guard_back_inner + d.guard_thickness + shift + 28
        add_solid(plot, load_part("test_black"), BLACK)
        add_solid(plot, load_part("bucket_glow"), GLOW)
        add_solid(plot, load_part("carrier_black"), BLACK)
        electronics(plot)
        add_solid(plot, load_part("guard_black"), BLACK, (0, shift, 0))
        for horizontal, vertical in GUARD_FASTENERS:
            z = d.eye_z + vertical
            nut(plot, horizontal, d.carrier_front + 0.9, z, PURPLE)
            fastener(plot, horizontal, z, seat, 20, PURPLE, reverse=True)
            guide_axis(plot, horizontal, z, d.carrier_front - 2, seat + 3, PURPLE)
        notes = [
            ("Preload 4 guard nuts", "Seat M2 nuts in the carrier's FRONT hex recesses before closing up. A small piece of tape can hold them temporarily.",
             (-41, d.carrier_front, 150), PURPLE),
            ("4 x M2 x 20 + washers", "Fit the guard from the candy side. Screws pass through the guard posts into those nuts; the lens module stays in place.",
             (41, seat + 2, 100), PURPLE),
            ("Keep top USB access clear", "Check the actual plug in the 22 x 23 mm top opening. Switch/reset and battery connector are serviced with the guard removed.",
             (0, d.front + 17.5 + shift, d.eye_z + 47), BLUE),
            ("Inspect the wiring first", "Connect the battery with correct polarity and slack, then check no lead is trapped at an edge or crossed by a screw.",
             (30, d.guard_back_inner + shift, 80), AMBER),
        ]
        caution = "Hold the coupon above the bench when fitting the guard. The shield is removable, not waterproof or a fireproof enclosure."
    elif name == "06_rope_and_final_checks":
        for part, color in (("bucket_black", BLACK), ("bucket_glow", GLOW),
                            ("carrier_black", BLACK), ("guard_black", BLACK)):
            add_solid(plot, load_part(part), color)
        electronics(plot)
        screw_heads(plot)
        y, z = d.rope_axis_y, d.rope_z
        for side in (-1, 1):
            plot.add_mesh(pv.Line((side * 88, y, z), (side * 115, y, z)).tube(radius=4.5),
                          color="#B59D73", smooth_shading=True)
            plot.add_mesh(pv.Sphere(radius=8, center=(side * 88, y, z)), color="#B59D73")
        points = [(-115, y, z), (-120, y, 221), (-90, y, 282), (0, y, 304),
                  (90, y, 282), (120, y, 221), (115, y, z)]
        plot.add_mesh(pv.Spline(points, 160).tube(radius=4.5), color="#B59D73", smooth_shading=True)
        add_ground(plot)
        notes = [
            ("Transfer the tested module", "Reuse the same skull, carrier, guard and hardware on the full bucket. The coupon is not a carrying-strength test.",
             (0, d.front - 8, d.eye_z), BLUE),
            ("Rope through both 13 mm bores", "Use approximately 8-10 mm nylon sail rope. Both holes remain 16.66 mm toward the eye; do not drill or relocate them.",
             (d.rope_anchor_inner_x + 5, y, z), AMBER),
            ("Stopper knots INSIDE", "Use substantial knots with adequate tails and equal rope legs. Confirm they cannot pull through. Rope and knots here are schematic.",
             (-88, y, z), AMBER),
            ("Check balance and carrying strength", "Hang just above padding, first empty, then with your intended evenly distributed load. Inspect the lugs and layer lines.",
             (0, y, 300), TEAL),
        ]
        caution = "No certified load rating. Stop at flexing, cracks or layer separation. Use wrapped candy; never charge under candy or unattended."
    else:
        raise ValueError(f"Unknown assembly step: {name}")
    _, _, camera, target, scale = STEPS[name]
    plot.camera_position = [camera, target, (0, 0, 1)]
    plot.camera.parallel_scale = scale
    return plot, notes, caution


def wrapped_text(draw, text, position, font, width, fill, line_height):
    x, y = position
    lines = []
    line = ""
    for word in text.split():
        if draw.textlength(word, font=font) > width:
            raise ValueError(f"Assembly caption word exceeds the text column: {word}")
        candidate = f"{line} {word}" if line else word
        if draw.textlength(candidate, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def render_step(name):
    title, subtitle, camera, target, scale = STEPS[name]
    plot, notes, caution = assembly_scene(name)
    try:
        plot.show(auto_close=False)
        pixels = plot.screenshot(return_img=True)
        if np.std(pixels) < 18 or len(np.unique(pixels[::15, ::15].reshape(-1, 3), axis=0)) < 100:
            raise ValueError(f"Blank assembly render: {name}")
        markers = []
        for _, _, point, _ in notes:
            plot.renderer.SetWorldPoint(*point, 1)
            plot.renderer.WorldToDisplay()
            x, y, _ = plot.renderer.GetDisplayPoint()
            if not (24 <= x <= 1136 and 24 <= y <= 936):
                raise ValueError(f"Assembly callout outside image: {name}, {point}")
            markers.append((round(x + 40), round(960 - y + 160)))
    finally:
        plot.close()
    image = Image.new("RGB", (1800, 1320), BACKGROUND)
    image.paste(Image.fromarray(pixels), (40, 160))
    draw = ImageDraw.Draw(image)
    font_dir = Path("/usr/share/fonts/truetype/dejavu")
    title_font = ImageFont.truetype(str(font_dir / "DejaVuSans-Bold.ttf"), 33)
    heading_font = ImageFont.truetype(str(font_dir / "DejaVuSans-Bold.ttf"), 23)
    body_font = ImageFont.truetype(str(font_dir / "DejaVuSans.ttf"), 22)
    small_font = ImageFont.truetype(str(font_dir / "DejaVuSans.ttf"), 20)
    draw.text((60, 30), "CYCLOPS CAULDRON / REVISION 07 / ASSEMBLY", font=small_font, fill="#526068")
    draw.text((60, 67), title, font=title_font, fill="#252D32")
    draw.text((60, 119), subtitle, font=body_font, fill="#526068")
    draw.line((1206, 177, 1206, 1110), fill="#BDCACD", width=2)
    for index, ((heading, body, _, color), (x, y)) in enumerate(zip(notes, markers, strict=True), start=1):
        draw.ellipse((x - 20, y - 20, x + 20, y + 20), fill=color, outline="white", width=3)
        draw.text((x, y), str(index), font=heading_font, anchor="mm", fill="white")
        top = 188 + (index - 1) * 216
        draw.ellipse((1230, top, 1268, top + 38), fill=color)
        draw.text((1249, top + 19), str(index), font=heading_font, anchor="mm", fill="white")
        bottom = wrapped_text(draw, heading, (1282, top + 2), heading_font, 458, "#252D32", 29)
        bottom = wrapped_text(draw, body, (1230, bottom + 17), body_font, 510, "#46555D", 29)
        if bottom > top + 204:
            raise ValueError(f"Assembly callout text overlaps: {name}, {index}")
    draw.rounded_rectangle((60, 1134, 1740, 1234), radius=12, fill="#F2E5CB")
    draw.text((80, 1146), "CHECK BEFORE CONTINUING", font=heading_font, fill="#77511F")
    bottom = wrapped_text(draw, caution, (80, 1180), small_font, 1640, "#594C39", 26)
    if bottom > 1232:
        raise ValueError(f"Assembly caution text overflows: {name}")
    draw.text((60, 1255), "Printed geometry = validated STL meshes. Electronics, hardware and rope are illustrative; threads omitted.",
              font=small_font, fill="#526068")
    draw.text((60, 1283), "Exploded gaps and arrows are not to scale. Hardware colours identify fasteners, not filament. Follow docs/ASSEMBLY.md.",
              font=small_font, fill="#526068")
    path = OUTPUT / f"{name}.png"
    image.save(path)
    print(f"Rendered assembly card: {path.name}", flush=True)
    return {"image": path.name, "sha256": file_sha256(path), "size": list(image.size),
            "nonblank": True, "callouts": len(notes), "camera": camera, "target": target, "parallel_scale": scale}


def main():
    validation = json.loads((ROOT / "docs/validation.json").read_text())
    if asdict(DIMENSIONS) != validation["parameters"]:
        raise ValueError("Assembly dimensions changed since CAD validation; rebuild before rendering")
    if not np.array_equal(BOARD_HOLES, validation["board_holes_relative_to_eye_mm"]):
        raise ValueError("PCB mounting pattern changed since CAD validation; rebuild before rendering")
    sources = {}
    for name in ("bucket_black", "bucket_glow", "test_black", "carrier_black", "guard_black"):
        source = ROOT / "print" / f"{name}.stl"
        digest = file_sha256(source)
        if digest != validation["files_sha256"][source.name]:
            raise ValueError(f"Mesh changed since CAD validation: {source.name}")
        sources[str(source.relative_to(ROOT))] = digest
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = [render_step(name) for name in STEPS]
    overview = Image.new("RGB", (1800, 1980), BACKGROUND)
    for index, record in enumerate(results):
        with Image.open(OUTPUT / record["image"]) as image:
            thumbnail = image.resize((900, 660), Image.Resampling.LANCZOS)
        overview.paste(thumbnail, ((index % 2) * 900, (index // 2) * 660))
    overview.save(OUTPUT / "overview.png")
    manifest = {
        "design": validation["design"],
        "source_meshes_sha256": sources,
        "generator_sha256": file_sha256(Path(__file__)),
        "render_helpers_sha256": file_sha256(ROOT / "tools/render.py"),
        "dimensions_source_sha256": file_sha256(ROOT / "design/bucket.py"),
        "images": results,
        "overview": {"image": "overview.png", "sha256": file_sha256(OUTPUT / "overview.png")},
        "limitations": [
            "Electronics, fasteners, battery, strap and rope are illustrative, not manufacturing geometry.",
            "Exploded spacing, alignment arrows and schematic knots are not dimensional instructions.",
            "Hardware colours distinguish fastener groups, not additional print materials.",
            "Physical hardware fit, optical performance and carrying strength have not been verified.",
        ],
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
