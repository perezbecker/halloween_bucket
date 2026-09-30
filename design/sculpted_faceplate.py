"""Shallow skull relief that reuses the already-printed revision-4 interfaces."""

from functools import lru_cache

import cadquery as cq

from design.bucket import (
    BUCKET_FASTENERS,
    DIMENSIONS,
    FACEPLATE_FASTENERS,
    block,
    cylinder_y,
    fuse,
    mass_properties,
    print_orientation,
    skull_glow,
    solid_volume,
)


MAXIMUM_THICKNESS = 6.2
SCREW_SEAT_RADIUS = 4.2
EYE_KEEP_FLAT_RADIUS = 26.2


@lru_cache(maxsize=None)
def original_plate():
    return print_orientation("bucket_glow", skull_glow())


def shallow_cap(center, radii, angle=0):
    transform = cq.Matrix([
        [radii[0], 0, 0, 0],
        [0, radii[1], 0, 0],
        [0, 0, radii[2], 0],
        [0, 0, 0, 1],
    ])
    sphere = cq.Workplane("XY").sphere(1).val().rotate((0, 0, 0), (0, 1, 0), 90).transformGeometry(transform)
    return sphere.rotate((0, 0, 0), (0, 0, 1), angle).translate(center)


def silhouette_columns():
    columns = []
    for face in original_plate().Faces():
        if face.geomType() == "PLANE" and face.normalAt().z > 0.99:
            columns.append(cq.Solid.extrudeLinear(
                face.outerWire(), face.innerWires(), cq.Vector(0, 0, MAXIMUM_THICKNESS)
            ).translate((0, 0, -0.15)))
    assert columns, "Missing the original plate's flat top face"
    return fuse(columns)


@lru_cache(maxsize=None)
def sculpted_plate():
    caps = [
        shallow_cap((0, 27, 2.2), (52, 24, 4.0)),
        shallow_cap((-27, 19, 2.3), (24, 10, 2.7), -12),
        shallow_cap((27, 19, 2.3), (24, 10, 2.7), 12),
        shallow_cap((-43, -13, 2.3), (17, 26, 2.8), -10),
        shallow_cap((43, -13, 2.3), (17, 26, 2.8), 10),
        shallow_cap((0, -67, 2.2), (34, 18, 2.9)),
    ]
    for horizontal in (-27, -16, -5.5, 5.5, 16, 27):
        caps.append(shallow_cap((horizontal * 0.9, -60, 2.5), (3.6, 10, 1.8)))
    relief = fuse(caps).intersect(silhouette_columns())
    clearances = []
    for horizontal, vertical in FACEPLATE_FASTENERS:
        clearances.append(cq.Solid.makeCone(
            SCREW_SEAT_RADIUS, SCREW_SEAT_RADIUS + 4.0, 5.0,
            cq.Vector(horizontal, vertical, DIMENSIONS.faceplate_thickness), cq.Vector(0, 0, 1),
        ))
    for horizontal, vertical in BUCKET_FASTENERS:
        clearances.append(cq.Solid.makeCone(
            4.2, 7.0, 5.0, cq.Vector(horizontal, vertical, DIMENSIONS.faceplate_thickness), cq.Vector(0, 0, 1),
        ))
    clearances.append(cq.Solid.makeCone(
        EYE_KEEP_FLAT_RADIUS, EYE_KEEP_FLAT_RADIUS + 2.0, 5.0,
        cq.Vector(0, 0, DIMENSIONS.faceplate_thickness), cq.Vector(0, 0, 1),
    ))
    relief = relief.cut(*clearances)
    return original_plate().fuse(relief).clean()


def assembled_plate():
    return sculpted_plate().rotate((0, 0, 0), (1, 0, 0), 90).translate(
        (0, DIMENSIONS.front, DIMENSIONS.eye_z)
    )


def verify_compatibility():
    original = original_plate()
    sculpted = sculpted_plate()
    assert sculpted.isValid() and len(sculpted.Solids()) == 1, "Relief is not one valid solid"
    original_bounds = original.BoundingBox()
    bounds = sculpted.BoundingBox()
    for attribute in ("xmin", "xmax", "ymin", "ymax", "zmin"):
        assert abs(getattr(bounds, attribute) - getattr(original_bounds, attribute)) < 1e-5
    assert bounds.zmax <= MAXIMUM_THICKNESS + 1e-5
    assert bounds.zmax > DIMENSIONS.faceplate_thickness + 2
    assert solid_volume(original.cut(sculpted)) < 1e-5, "Original seating geometry was removed"
    addition = sculpted.cut(original)
    lower_half = block(180, 180, 3.0, (0, -15, 1.5))
    assert solid_volume(addition.intersect(lower_half)) < 1e-5, "Relief changed the original 3 mm layer"
    clear_eye = cq.Solid.makeCylinder(DIMENSIONS.eye_bore / 2, 10, cq.Vector(0, 0, -1))
    assert solid_volume(sculpted.intersect(clear_eye)) < 1e-5, "The original eye bore was narrowed"
    flat_eye = cq.Solid.makeCylinder(EYE_KEEP_FLAT_RADIUS - 0.01, 5, cq.Vector(0, 0, 3.001))
    assert solid_volume(sculpted.intersect(flat_eye)) < 1e-5, "Relief intrudes on the existing lens bezel"
    for horizontal, vertical in FACEPLATE_FASTENERS:
        seat = cq.Solid.makeCylinder(SCREW_SEAT_RADIUS - 0.01, 5,
                                    cq.Vector(horizontal, vertical, 3.001))
        assert solid_volume(sculpted.intersect(seat)) < 1e-5, "An M2 screw needs a longer grip length"
        bore = cq.Solid.makeCylinder(DIMENSIONS.m2_clearance / 2, 10,
                                    cq.Vector(horizontal, vertical, -1))
        assert solid_volume(sculpted.intersect(bore)) < 1e-5, "M2 attachment bore blocked"
    for horizontal, vertical in BUCKET_FASTENERS:
        access = cq.Solid.makeCylinder(3.5, 10, cq.Vector(horizontal, vertical, -1))
        assert solid_volume(sculpted.intersect(access)) < 1e-5, "Carrier screw access blocked"
    installed = assembled_plate()
    rear_half = block(200, 80, 210, (0, DIMENSIONS.front + 40, DIMENSIONS.eye_z))
    assert solid_volume(installed.intersect(rear_half)) < 1e-5, "New material extends behind the old mounting plane"
    lens = cylinder_y(20, DIMENSIONS.front - 20, 60, 0, DIMENSIONS.eye_z)
    assert solid_volume(installed.intersect(lens)) < 1e-5, "Lens diameter clearance lost"
    volume, center = mass_properties(sculpted)
    return {
        "original_plate_preserved": True,
        "rear_surface_outline_and_holes_unchanged": True,
        "existing_m2_x_10_screws_retained": True,
        "eye_bezel_and_carrier_access_unchanged": True,
        "maximum_thickness_mm": bounds.zmax,
        "seating_thickness_mm": DIMENSIONS.faceplate_thickness,
        "original_volume_cm3": solid_volume(original) / 1000,
        "sculpted_volume_cm3": volume / 1000,
        "added_volume_cm3": solid_volume(addition) / 1000,
        "print_center_of_mass_mm": center,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(verify_compatibility(), indent=2))