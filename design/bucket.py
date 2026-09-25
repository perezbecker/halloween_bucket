"""Single-nozzle skull cauldron. Millimeters; front is -Y, build direction +Z."""

from dataclasses import dataclass
from functools import lru_cache
import math

import cadquery as cq
import numpy as np
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from scipy.interpolate import PchipInterpolator


@dataclass(frozen=True)
class Dimensions:
    height: float = 200.0
    belly_radius: float = 112.0
    neck_radius: float = 93.0
    base_radius: float = 73.0
    wall: float = 3.0
    floor: float = 3.6
    rim_radius: float = 4.0
    front: float = -89.0
    eye_z: float = 125.0
    eye_bore: float = 44.4
    rope_bore: float = 13.0
    rope_drop: float = 22.0
    faceplate_thickness: float = 3.0
    carrier_thickness: float = 3.0
    pcb_thickness: float = 1.6
    rear_clearance: float = 12.0
    guard_thickness: float = 2.0
    lens_holder_thickness: float = 2.8
    lens_standoff: float = 6.0
    rear_pcb_screw_length: float = 20.0
    rear_pcb_washer: float = 1.0
    m2_clearance: float = 2.4
    m25_clearance: float = 2.9
    vertical_adjustment: float = 2.0
    battery_width: float = 29.0
    battery_height: float = 36.0
    battery_thickness: float = 4.75
    battery_pocket_width: float = 33.0
    battery_pocket_height: float = 42.0
    battery_pocket_depth: float = 8.5

    @property
    def rope_z(self) -> float:
        return self.height - self.rope_drop

    @property
    def rope_anchor_inner_x(self) -> float:
        return float(cauldron_radius_profile()(self.rope_z)) - 6.0

    @property
    def inner_front(self) -> float:
        return self.front + self.wall

    @property
    def carrier_front(self) -> float:
        return self.pcb_rear + self.rear_clearance

    @property
    def pcb_rear(self) -> float:
        return self.front + 16.9

    @property
    def guard_back_inner(self) -> float:
        return self.front + 43.5

    @property
    def carrier_back(self) -> float:
        return self.carrier_front + self.carrier_thickness

    @property
    def pcb_front(self) -> float:
        return self.pcb_rear - self.pcb_thickness

    @property
    def holder_front(self) -> float:
        return self.pcb_front - self.lens_standoff - self.lens_holder_thickness


DIMENSIONS = Dimensions()


@dataclass(frozen=True)
class BalanceParameters:
    black_density_g_cm3: float = 1.24
    glow_density_g_cm3: float = 1.50
    board_mass_g: float = 17.5
    battery_mass_g: float = 10.5
    glass_mass_g: float = 31.0
    lens_kit_mass_g: float = 5.0
    fasteners_mass_g: float = 12.0
    strap_pad_mass_g: float = 3.0
    design_payload_g: float = 0.0
    payload_center_mm: tuple = (0.0, 0.0, 65.0)


BALANCE = BalanceParameters()
OPTICAL_CENTER_EAGLE_Y = 3.082925
BOARD_HOLES = tuple(
    (horizontal, vertical - OPTICAL_CENTER_EAGLE_Y)
    for vertical in (-18.161, 27.559)
    for horizontal in (-8.89, 8.89)
)
BUCKET_FASTENERS = tuple(
    (horizontal, vertical) for horizontal in (-40.0, 40.0) for vertical in (-35.0, 35.0)
)
GUARD_FASTENERS = tuple(
    (horizontal, vertical) for horizontal in (-41.0, 41.0) for vertical in (-25.0, 25.0)
)
FACEPLATE_FASTENERS = tuple(
    (horizontal, vertical) for horizontal in (-30.0, 30.0) for vertical in (-45.0, 40.0)
)


@lru_cache(maxsize=256)
def mass_properties(shape):
    if not shape.Solids():
        return 0.0, (0.0, 0.0, 0.0)
    properties = GProp_GProps()
    error = BRepGProp.VolumePropertiesGK_s(shape.wrapped, properties, 1e-8, True, True, True, False, False)
    if error < 0:
        raise ValueError("Spline-span mass integration failed")
    center = properties.CentreOfMass()
    return properties.Mass(), (center.X(), center.Y(), center.Z())


def solid_volume(shape):
    return mass_properties(shape)[0]


def block(width, depth, height, center):
    return cq.Workplane("XY").box(width, depth, height).translate(center).val()


def cylinder_y(radius, start_y, length, horizontal, vertical):
    return cq.Solid.makeCylinder(
        radius, length, cq.Vector(horizontal, start_y, vertical), cq.Vector(0, 1, 0)
    )


def fuse(shapes):
    shapes = list(shapes)
    return shapes[0].fuse(*shapes[1:]).clean() if len(shapes) > 1 else shapes[0]


def rounded_profile(width, depth, radius, height=0.0, center_y=0.0):
    half_width, half_depth = width / 2, depth / 2
    return (
        cq.Workplane("XY", origin=(0, center_y, height))
        .moveTo(-half_width + radius, -half_depth)
        .lineTo(half_width - radius, -half_depth)
        .radiusArc((half_width, -half_depth + radius), -radius)
        .lineTo(half_width, half_depth - radius)
        .radiusArc((half_width - radius, half_depth), -radius)
        .lineTo(-half_width + radius, half_depth)
        .radiusArc((-half_width, half_depth - radius), -radius)
        .lineTo(-half_width, -half_depth + radius)
        .radiusArc((-half_width + radius, -half_depth), -radius)
        .close()
        .val()
    )


def flat_panel(width, height, radius, front_y, thickness, center_z):
    wire = rounded_profile(width, height, radius)
    solid = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, thickness))
    return solid.rotate((0, 0, 0), (1, 0, 0), 90).translate(
        (0, front_y + thickness, center_z)
    )


def vertical_slot(horizontal, vertical, front_y, depth, diameter, travel):
    radius = diameter / 2
    return fuse(
        [
            cylinder_y(radius, front_y, depth, horizontal, vertical - travel),
            cylinder_y(radius, front_y, depth, horizontal, vertical + travel),
            block(diameter, depth, 2 * travel, (horizontal, front_y + depth / 2, vertical)),
        ]
    )


def hex_pocket(horizontal, vertical, front_y, depth, across_flats=4.3):
    radius = across_flats / math.sqrt(3)
    points = [
        (radius * math.cos(math.radians(angle)), radius * math.sin(math.radians(angle)))
        for angle in range(30, 390, 60)
    ]
    wire = cq.Workplane("XY").polyline(points).close().val()
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, depth)).rotate(
        (0, 0, 0), (1, 0, 0), 90
    ).translate((horizontal, front_y + depth, vertical))


def cauldron_radius_profile():
    station_heights = np.array([0, 18, 38, 52, 90, 128, 166, 188, 199, 204], dtype=float)
    profile_top = DIMENSIONS.height - 6
    station_heights = np.where(station_heights > 52,
                               52 + (station_heights - 52) * (profile_top - 52) / 152,
                               station_heights)
    station_radii = np.array([
        DIMENSIONS.base_radius,
        90 * DIMENSIONS.belly_radius / 120,
        103 * DIMENSIONS.belly_radius / 120,
        111 * DIMENSIONS.belly_radius / 120,
        DIMENSIONS.belly_radius, DIMENSIONS.belly_radius,
        115 * DIMENSIONS.belly_radius / 120, 107 * DIMENSIONS.belly_radius / 120,
        DIMENSIONS.neck_radius + 1.5, DIMENSIONS.neck_radius,
    ])
    return PchipInterpolator(station_heights, station_radii)


def cauldron_envelope(inner=False):
    radius_at = cauldron_radius_profile()
    station_heights = radius_at.x
    profile_top = DIMENSIONS.height - 6
    heights = np.unique(np.concatenate((np.linspace(0, profile_top, 103), station_heights)))
    radii = radius_at(heights)
    if inner:
        slopes = radius_at.derivative()(heights)
        normal_lengths = np.sqrt(1 + slopes ** 2)
        radii = radii - (DIMENSIONS.wall + 0.1) / normal_lengths
        heights = heights + (DIMENSIONS.wall + 0.1) * slopes / normal_lengths
        assert np.all(np.diff(heights) > 0), "Inner cauldron profile folds over itself"
        floor_radius = float(PchipInterpolator(heights, radii)(DIMENSIONS.floor))
        keep = heights > DIMENSIONS.floor
        heights = np.concatenate(([DIMENSIONS.floor], heights[keep], [DIMENSIONS.height + 1]))
        radii = np.concatenate(([floor_radius], radii[keep], [DIMENSIONS.neck_radius - DIMENSIONS.wall - 0.1]))
    profile = PchipInterpolator(heights, radii) if inner else radius_at
    heights = profile.x
    radii = profile(heights)
    slopes = profile.derivative()(heights)
    points = [cq.Vector(float(radius), 0, float(height))
              for radius, height in zip(radii, heights, strict=True)]
    bottom_axis = cq.Vector(0, 0, float(heights[0]))
    top_axis = cq.Vector(0, 0, float(heights[-1]))
    edges = [cq.Edge.makeLine(bottom_axis, points[0])]
    for index in range(len(points) - 1):
        step = float(heights[index + 1] - heights[index]) / 3
        controls = [points[index],
                    points[index] + cq.Vector(float(slopes[index]) * step, 0, step),
                    points[index + 1] - cq.Vector(float(slopes[index + 1]) * step, 0, step),
                    points[index + 1]]
        if max(abs(float(slopes[index])), abs(float(slopes[index + 1]))) < 1e-10 and abs(radii[index] - radii[index + 1]) < 1e-10:
            edges.append(cq.Edge.makeLine(points[index], points[index + 1]))
        else:
            edges.append(cq.Edge.makeBezier(controls))
    edges.extend([cq.Edge.makeLine(points[-1], top_axis), cq.Edge.makeLine(top_axis, bottom_axis)])
    profile_wire = cq.Wire.assembleEdges(edges)
    envelope = cq.Solid.revolve(profile_wire, [], 360, cq.Vector(0, 0, 0), cq.Vector(0, 0, 1))
    front = DIMENSIONS.inner_front if inner else DIMENSIONS.front
    transition_z = 188 + (DIMENSIONS.wall * (math.sqrt(2) - 1) if inner else 0)
    front_cut = (
        cq.Workplane("YZ", origin=(-200, 0, 0))
        .polyline([(front - 200, -1), (front, -1), (front, transition_z),
                   (front - 40, transition_z + 40), (front - 200, transition_z + 40)])
        .close().extrude(400).val()
    )
    return envelope.cut(front_cut).clean()


@lru_cache(maxsize=None)
def cauldron_body():
    shell = cauldron_envelope().cut(cauldron_envelope(inner=True))
    rim = cq.Solid.makeTorus(
        DIMENSIONS.neck_radius, DIMENSIONS.rim_radius,
        cq.Vector(0, 0, DIMENSIONS.height - DIMENSIONS.rim_radius), cq.Vector(0, 0, 1),
    )
    return fuse([shell, rim])


@lru_cache(maxsize=None)
def bucket_shell(rope_y=None):
    if rope_y is None:
        rope_y = balanced_rope_y()
    shell = cauldron_body()
    bosses = []
    rope_cuts = []
    anchor_inner_x = DIMENSIONS.rope_anchor_inner_x
    for direction in (-1, 1):
        boss = cq.Solid.makeCylinder(
            17.0,
            10.0,
            cq.Vector(direction * anchor_inner_x, rope_y, DIMENSIONS.rope_z),
            cq.Vector(direction, 0, 0),
        )
        bosses.append(boss)
        rope_cuts.append(
            cq.Solid.makeCylinder(
                DIMENSIONS.rope_bore / 2,
                28,
                cq.Vector(direction * (anchor_inner_x - 8), rope_y, DIMENSIONS.rope_z),
                cq.Vector(direction, 0, 0),
            )
        )
        rope_cuts.append(
            cq.Solid.makeCone(
                DIMENSIONS.rope_bore / 2,
                DIMENSIONS.rope_bore / 2 + 1,
                1.1,
                cq.Vector(direction * (anchor_inner_x + 8.9), rope_y, DIMENSIONS.rope_z),
                cq.Vector(direction, 0, 0),
            )
        )
        rope_cuts.append(
            cq.Solid.makeCone(
                DIMENSIONS.rope_bore / 2 + 1,
                DIMENSIONS.rope_bore / 2,
                1.1,
                cq.Vector(direction * anchor_inner_x, rope_y, DIMENSIONS.rope_z),
                cq.Vector(direction, 0, 0),
            )
        )
    shell = fuse([shell, *bosses]).cut(*rope_cuts)
    return shell.cut(*panel_holes()).clean()


def panel_holes():
    cuts = [cylinder_y(DIMENSIONS.eye_bore / 2, DIMENSIONS.front - 15, 35, 0, DIMENSIONS.eye_z)]
    for horizontal, vertical in BUCKET_FASTENERS:
        cuts.append(
            cylinder_y(DIMENSIONS.m2_clearance / 2, DIMENSIONS.front - 10, 24, horizontal, DIMENSIONS.eye_z + vertical)
        )
    for horizontal, vertical in FACEPLATE_FASTENERS:
        cuts.append(cylinder_y(DIMENSIONS.m2_clearance / 2, DIMENSIONS.front - 10, 24,
                               horizontal, DIMENSIONS.eye_z + vertical))
    return cuts


def skull_wire():
    return (
        cq.Workplane("XY")
        .moveTo(0, 194)
        .threePointArc((47, 183), (63, 163))
        .threePointArc((71, 143), (62, 123))
        .lineTo(69, 111)
        .lineTo(61, 102)
        .lineTo(49, 105)
        .lineTo(43, 93)
        .lineTo(46, 65)
        .threePointArc((34, 48), (0, 45))
        .threePointArc((-34, 48), (-46, 65))
        .lineTo(-43, 93)
        .lineTo(-49, 105)
        .lineTo(-61, 102)
        .lineTo(-69, 111)
        .lineTo(-62, 123)
        .threePointArc((-71, 143), (-63, 163))
        .threePointArc((-47, 183), (0, 194))
        .close()
        .val()
    )


def skull_artwork(wire):
    return wire.scale(0.90).translate((0, DIMENSIONS.eye_z - 139 * 0.90, 0))


def front_extrusion(wire, thickness, back_y):
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, thickness)).rotate(
        (0, 0, 0), (1, 0, 0), 90
    ).translate((0, back_y, 0))


def skull_polygon(points, thickness=12.0, back_y=None):
    wire = skull_artwork(cq.Workplane("XY").polyline(points).close().val())
    return front_extrusion(wire, thickness, DIMENSIONS.front + 5 if back_y is None else back_y)


@lru_cache(maxsize=None)
def skull_glow():
    thickness = DIMENSIONS.faceplate_thickness
    skull = front_extrusion(skull_artwork(skull_wire()), thickness, DIMENSIONS.front)
    socket = (
        cq.Workplane("XY")
        .moveTo(0, 163)
        .threePointArc((27, 164), (33, 145))
        .threePointArc((24, 112), (0, 112))
        .threePointArc((-24, 112), (-33, 145))
        .threePointArc((-27, 164), (0, 163))
        .close().val()
    )
    skull = skull.cut(front_extrusion(skull_artwork(socket), 12, DIMENSIONS.front + 5))
    nose = skull_polygon([(-3, 106), (-13, 91), (-8, 85), (0, 91), (8, 85), (13, 91), (3, 106)])
    mouth = skull_polygon(
        [(-37, 78), (-29, 81), (-18, 77), (0, 75), (18, 77), (29, 81), (37, 78),
         (34, 60), (25, 56), (0, 54), (-25, 56), (-34, 60)]
    )
    cracks = [
        skull_polygon([(-20, 190), (-17, 177), (-25, 173), (-22, 163), (-19, 170), (-12, 175), (-15, 191)]),
        skull_polygon([(39, 175), (31, 170), (34, 164), (37, 169), (44, 173)]),
        skull_polygon([(-62, 115), (-51, 117), (-42, 109), (-50, 112), (-60, 111)]),
        skull_polygon([(62, 115), (51, 117), (42, 109), (50, 112), (60, 111)]),
    ]
    skull = skull.cut(nose, mouth, *cracks)
    teeth = []
    for horizontal in (-27, -16, -5.5, 5.5, 16, 27):
        fang = abs(horizontal) == 27
        top = 83 if fang else 79
        bottom = 60 if fang else 65
        teeth.append(skull_polygon(
            [(horizontal - 4, top), (horizontal + 4, top),
             (horizontal + (2 if fang else 3), bottom), (horizontal - 3, bottom + 1)],
            thickness, DIMENSIONS.front,
        ))
    bezel = cylinder_y(26.0, DIMENSIONS.front - thickness, thickness, 0, DIMENSIONS.eye_z).cut(
        cylinder_y(DIMENSIONS.eye_bore / 2, DIMENSIONS.front - 5, 8, 0, DIMENSIONS.eye_z)
    )
    ornament = fuse([skull, *teeth, bezel])
    recesses = [
        cylinder_y(3.5, DIMENSIONS.front - 8, 15, horizontal, DIMENSIONS.eye_z + vertical)
        for horizontal, vertical in BUCKET_FASTENERS
    ]
    return ornament.cut(*recesses, *panel_holes()).clean()


@lru_cache(maxsize=None)
def bucket_black():
    return bucket_shell()


@lru_cache(maxsize=None)
def carrier():
    plate = flat_panel(96, 90, 5, DIMENSIONS.carrier_front, DIMENSIONS.carrier_thickness, DIMENSIONS.eye_z)
    plate = plate.cut(block(70, 8, 74, (0, DIMENSIONS.carrier_front + 1, DIMENSIONS.eye_z)))
    pieces = [plate]
    cuts = []
    for horizontal, vertical in BOARD_HOLES:
        pieces.append(
            block(38, DIMENSIONS.carrier_thickness, 7, (math.copysign(24, horizontal),
                                             DIMENSIONS.carrier_front + DIMENSIONS.carrier_thickness / 2,
                                             DIMENSIONS.eye_z + vertical))
        )
        pieces.append(cylinder_y(2.8, DIMENSIONS.pcb_rear, DIMENSIONS.rear_clearance, horizontal, DIMENSIONS.eye_z + vertical))
        cuts.append(cylinder_y(DIMENSIONS.m25_clearance / 2, DIMENSIONS.pcb_rear - 1, 19, horizontal, DIMENSIONS.eye_z + vertical))
    for horizontal, vertical in BUCKET_FASTENERS:
        pieces.append(
            cylinder_y(5.5, DIMENSIONS.inner_front, DIMENSIONS.carrier_front - DIMENSIONS.inner_front,
                       horizontal, DIMENSIONS.eye_z + vertical)
        )
        cuts.append(vertical_slot(horizontal, DIMENSIONS.eye_z + vertical, DIMENSIONS.inner_front - 1, 36,
                                  DIMENSIONS.m2_clearance, DIMENSIONS.vertical_adjustment))
        cuts.append(
            block(4.3, 1.81, 8.8,
                  (horizontal, DIMENSIONS.carrier_back - 0.9, DIMENSIONS.eye_z + vertical))
        )
    for horizontal, vertical in GUARD_FASTENERS:
        cuts.append(cylinder_y(DIMENSIONS.m2_clearance / 2, DIMENSIONS.carrier_front - 2, 22,
                               horizontal, DIMENSIONS.eye_z + vertical))
        cuts.append(hex_pocket(horizontal, DIMENSIONS.eye_z + vertical, DIMENSIONS.carrier_front - 0.01, 1.81))
    return fuse(pieces).cut(*cuts).clean()


@lru_cache(maxsize=None)
def guard():
    front = DIMENSIONS.inner_front + 1.0
    back = DIMENSIONS.guard_back_inner + DIMENSIONS.guard_thickness
    guard_top = DIMENSIONS.eye_z + 49
    guard_height = guard_top - 50
    guard_center_z = (guard_top + 50) / 2
    outer = flat_panel(106, guard_height, 6, front, back - front, guard_center_z)
    inner = flat_panel(106 - 2 * DIMENSIONS.guard_thickness, guard_height - 2 * DIMENSIONS.guard_thickness,
                       6 - DIMENSIONS.guard_thickness, front - 0.5,
                       DIMENSIONS.guard_back_inner - front + 0.5, guard_center_z)
    shell = outer.cut(inner)
    cradle_bottom = 59.0
    seat = DIMENSIONS.guard_back_inner
    pocket_front = seat - DIMENSIONS.battery_pocket_depth
    rails = [
        block(DIMENSIONS.battery_pocket_width + 4, DIMENSIONS.battery_pocket_depth, 2.4,
              (0, seat - DIMENSIONS.battery_pocket_depth / 2, cradle_bottom - 1.2)),
    ]
    for direction in (-1, 1):
        rails.append(
            block(2, DIMENSIONS.battery_pocket_depth, DIMENSIONS.battery_pocket_height,
                  (direction * (DIMENSIONS.battery_pocket_width / 2 + 1),
                   seat - DIMENSIONS.battery_pocket_depth / 2,
                   cradle_bottom + DIMENSIONS.battery_pocket_height / 2))
        )
    for horizontal, vertical in GUARD_FASTENERS:
        rails.append(
            cylinder_y(4.5, DIMENSIONS.carrier_back, DIMENSIONS.guard_back_inner - DIMENSIONS.carrier_back,
                       horizontal, DIMENSIONS.eye_z + vertical)
        )
    shell = fuse([shell, *rails])
    cuts = []
    for horizontal, vertical in GUARD_FASTENERS:
        cuts.append(cylinder_y(DIMENSIONS.m2_clearance / 2, DIMENSIONS.carrier_back - 1, back - DIMENSIONS.carrier_back + 2,
                               horizontal, DIMENSIONS.eye_z + vertical))
    for horizontal in (-21.5, 21.5):
        cuts.append(block(2.6, 8, 11, (horizontal, back - 1, 80)))
    cuts.append(block(22, 23, 20, (0, DIMENSIONS.front + 17.5, guard_top - 4)))
    for vertical in (110, 119, 128):
        cuts.append(block(1.5, 8, 4, (28, back - 1, vertical)))
        cuts.append(block(1.5, 8, 4, (-28, back - 1, vertical)))
    return shell.cut(*cuts).clean()


def assembly_mass_components(black_shape, black_density=None, glow_density=None, glass_mass=None):
    black_density = BALANCE.black_density_g_cm3 if black_density is None else black_density
    glow_density = BALANCE.glow_density_g_cm3 if glow_density is None else glow_density
    glass_mass = BALANCE.glass_mass_g if glass_mass is None else glass_mass
    components = []
    for name, shape, density in (
        ("Cauldron body and rope lugs", black_shape, black_density),
        ("One-eyed glow skull", skull_glow(), glow_density),
        ("HalloWing carrier", carrier(), black_density),
        ("Battery cradle and candy guard", guard(), black_density),
    ):
        volume, center = mass_properties(shape)
        components.append({"name": name, "mass_g": volume * density / 1000,
                           "center_mm": center, "basis": "CAD solid volume x nominal density"})
    for name, mass, center, basis in (
        ("HalloWing M0", BALANCE.board_mass_g,
         (0, DIMENSIONS.pcb_rear + 3, DIMENSIONS.eye_z - OPTICAL_CENTER_EAGLE_Y), "Adafruit listed mass; estimated component center"),
        ("500 mAh LiPo", BALANCE.battery_mass_g,
         (0, DIMENSIONS.guard_back_inner - 3.4, 78), "Adafruit listed mass; battery bay center"),
        ("40 mm glass lens", glass_mass,
         (0, DIMENSIONS.holder_front + DIMENSIONS.lens_holder_thickness - 5.8, DIMENSIONS.eye_z), "Estimated glass spherical-cap mass and center; weigh actual lens"),
        ("Acrylic and stock lens hardware", BALANCE.lens_kit_mass_g,
         (0, DIMENSIONS.holder_front + 1.5, DIMENSIONS.eye_z + 1.6), "Estimated kit mass; weigh actual kit"),
        ("M2 and M2.5 fasteners and washers", BALANCE.fasteners_mass_g,
         (0, DIMENSIONS.front + 23.0, DIMENSIONS.eye_z), "Estimated hardware mass and aggregate center"),
        ("Four M2 x 10 faceplate screws, nuts and washers", 3.0,
         (0, DIMENSIONS.front + 1.0, DIMENSIONS.eye_z - 2.5), "Estimated hardware mass"),
        ("Soft battery strap and insulating pad", BALANCE.strap_pad_mass_g,
         (0, DIMENSIONS.guard_back_inner - 3.0, 80), "Estimated mass"),
    ):
        components.append({"name": name, "mass_g": mass, "center_mm": center, "basis": basis})
    return components


def combined_mass_center(components, payload_g=0.0, payload_center=None):
    payload_center = BALANCE.payload_center_mm if payload_center is None else payload_center
    total_mass = sum(component["mass_g"] for component in components) + payload_g
    moment = sum((component["mass_g"] * np.asarray(component["center_mm"])
                  for component in components), np.zeros(3))
    center = (moment + payload_g * np.asarray(payload_center)) / total_mass
    return total_mass, tuple(float(coordinate) for coordinate in center)


@lru_cache(maxsize=None)
def balanced_rope_y():
    unanchored = cauldron_body().cut(*panel_holes()).clean()
    components = assembly_mass_components(unanchored)
    _, center = combined_mass_center(components, BALANCE.design_payload_g)
    rope_y = center[1]
    for _ in range(6):
        body = bucket_shell(rope_y)
        components = assembly_mass_components(body)
        _, center = combined_mass_center(components, BALANCE.design_payload_g)
        if abs(center[1] - rope_y) < 0.002:
            return round(center[1], 2)
        rope_y = center[1]
    raise ValueError("Rope-axis mass balance did not converge")


def balance_report():
    rope_y = balanced_rope_y()
    components = assembly_mass_components(bucket_black())
    total_mass, center = combined_mass_center(components, BALANCE.design_payload_g)
    vertical_arm = DIMENSIONS.rope_z - center[2]
    assert vertical_arm > 40, "Center of mass is too close to or above the rope axis"
    assert abs(center[1] - rope_y) < 0.02, "Rope holes miss the assembled center of mass"
    assert abs(center[0]) < 0.5, "Unacceptable left-right mass asymmetry"
    assert rope_y < -1, "Electronics mass was not included in the rope compensation"
    scenarios = []
    for payload in (0, 500, 1000):
        mass, payload_center = combined_mass_center(components, payload)
        tilt = math.degrees(math.atan2(payload_center[1] - rope_y, DIMENSIONS.rope_z - payload_center[2]))
        scenarios.append({"payload_g": payload, "total_mass_g": mass,
                          "center_mm": payload_center, "predicted_pitch_degrees": tilt})
    sensitivity = []
    for black_density in (1.20, 1.30):
        for glow_density in (1.30, 2.00):
            for glass_mass in (22.0, 40.0):
                changed = assembly_mass_components(bucket_black(), black_density, glow_density, glass_mass)
                _, shifted = combined_mass_center(changed, BALANCE.design_payload_g)
                tilt = math.degrees(math.atan2(shifted[1] - rope_y, DIMENSIONS.rope_z - shifted[2]))
                sensitivity.append(tilt)
    old_tilt = math.degrees(math.atan2(center[1], vertical_arm))
    anchor_x = DIMENSIONS.rope_anchor_inner_x + 5.0
    return {
        "target": "Assembled cauldron including all electronics; excludes the test coupon and removed print supports",
        "design_payload_g": BALANCE.design_payload_g,
        "payload_center_assumption_mm": BALANCE.payload_center_mm,
        "rope_axis_y_mm": rope_y,
        "rope_axis_z_mm": DIMENSIONS.rope_z,
        "anchor_centers_mm": [(-anchor_x, rope_y, DIMENSIONS.rope_z), (anchor_x, rope_y, DIMENSIONS.rope_z)],
        "assembled_mass_g": total_mass,
        "assembled_center_mm": center,
        "residual_fore_aft_offset_mm": center[1] - rope_y,
        "predicted_pitch_if_holes_were_at_y_zero_degrees": old_tilt,
        "left_right_load_share": [(anchor_x - center[0]) / (2 * anchor_x), (anchor_x + center[0]) / (2 * anchor_x)],
        "components": components,
        "centered_candy_scenarios": scenarios,
        "density_and_lens_mass_sensitivity_pitch_degrees": [min(sensitivity), max(sensitivity)],
        "limitations": [
            "This is a static estimate, not a measured hanging test or certified rope-load rating.",
            "The black and glow density estimates are independent of the conservative filament budget densities.",
            "Printed infill, actual lens/fastener masses, unequal rope ends, and uneven candy can change balance.",
            "No fixed pair of holes can stay exactly level for every possible candy distribution.",
        ],
    }


@lru_cache(maxsize=None)
def coupon_black():
    region = block(106, 14, 100, (0, DIMENSIONS.front, DIMENSIONS.eye_z))
    panel = bucket_black().intersect(region)
    assert solid_volume(panel) > 18000, "The mounting coupon lost its wall section"
    foot = block(116, 27.8, 3, (0, DIMENSIONS.front + 14.1, DIMENSIONS.eye_z - 51.5))
    guard_clearance = block(108, 60, 12, (0, DIMENSIONS.front + 33.5, DIMENSIONS.eye_z - 50))
    foot = foot.cut(guard_clearance)
    return panel.fuse(foot).clean()


@lru_cache(maxsize=None)
def coupon_glow():
    region = block(106, 14, 100, (0, DIMENSIONS.front, DIMENSIONS.eye_z))
    return skull_glow().intersect(region).clean()


def print_orientation(name, shape):
    if name in ("bucket_glow", "test_glow"):
        oriented = shape.rotate((0, 0, 0), (1, 0, 0), -90)
        return oriented.translate((0, -DIMENSIONS.eye_z, DIMENSIONS.front))
    if name in ("carrier_black", "guard_black"):
        oriented = shape.rotate((0, 0, 0), (1, 0, 0), -90)
        bounds = oriented.BoundingBox()
        return oriented.translate((0, -DIMENSIONS.eye_z, -bounds.zmin))
    if name.startswith("test_"):
        return shape.translate((0, -DIMENSIONS.front, -(DIMENSIONS.eye_z - 53.0)))
    return shape


def verify_faceplate():
    skull = skull_glow()
    assert skull.isValid() and len(skull.Solids()) == 1, "Faceplate must be one printable solid"
    assert solid_volume(bucket_black().intersect(skull)) < 1e-5, "Separate faceplate overlaps body"
    for horizontal, vertical in FACEPLATE_FASTENERS:
        height = DIMENSIONS.eye_z + vertical
        bore = cylinder_y(1.0, DIMENSIONS.front - 4, 12, horizontal, height)
        assert solid_volume(skull.intersect(bore)) < 1e-6, "Faceplate screw passage obstructed"
        washer_land = cylinder_y(2.8, DIMENSIONS.front - 2.9, 2.8, horizontal, height).cut(
            cylinder_y(1.3, DIMENSIONS.front - 3, 3, horizontal, height)
        )
        assert solid_volume(washer_land.cut(skull)) < 1e-5, "Insufficient plastic around faceplate screw"
        hardware = cylinder_y(2.6, DIMENSIONS.inner_front, 5, horizontal, height)
        assert solid_volume(carrier().intersect(hardware)) < 1e-5, "Faceplate hardware hits carrier"
        assert solid_volume(guard().intersect(hardware)) < 1e-5, "Faceplate hardware hits guard"
    oriented = print_orientation("bucket_glow", skull)
    assert abs(oriented.BoundingBox().zmin) < 1e-6
    assert abs(oriented.BoundingBox().zlen - DIMENSIONS.faceplate_thickness) < 1e-5
    return {"separate_flat_faceplate": True, "m2_attachment_points": len(FACEPLATE_FASTENERS),
            "faceplate_thickness_mm": DIMENSIONS.faceplate_thickness}


def print_parts(include_bucket=True):
    parts = {
        "carrier_black": carrier(),
        "guard_black": guard(),
        "test_black": coupon_black(),
    }
    if include_bucket:
        parts = {"bucket_black": bucket_black(), "bucket_glow": skull_glow(), **parts}
    return {name: print_orientation(name, shape) for name, shape in parts.items()}


def verify_mount():
    mount = carrier()
    assert mount.isValid(), "Carrier CAD solid is invalid"
    assert len(mount.Solids()) == 1, "Carrier must be one connected solid"
    assert math.isclose(BOARD_HOLES[1][0] - BOARD_HOLES[0][0], 17.78)
    assert math.isclose(BOARD_HOLES[2][1] - BOARD_HOLES[0][1], 45.72)
    for horizontal, vertical in BOARD_HOLES:
        axis = cylinder_y(1.3, DIMENSIONS.pcb_rear - 0.1, 15.5, horizontal, DIMENSIONS.eye_z + vertical)
        assert solid_volume(mount.intersect(axis)) < 1e-6, "PCB screw passage obstructed"
        contact = cylinder_y(2.7, DIMENSIONS.pcb_rear, 0.2, horizontal, DIMENSIONS.eye_z + vertical)
        assert solid_volume(mount.intersect(contact)) > 2, "Missing PCB support face"
    assert DIMENSIONS.rear_clearance >= 11, "Insufficient rear component clearance"
    assert DIMENSIONS.battery_pocket_width > DIMENSIONS.battery_width + 2
    assert DIMENSIONS.battery_pocket_height > DIMENSIONS.battery_height + 4
    assert DIMENSIONS.battery_pocket_depth > DIMENSIONS.battery_thickness + 2
    rear_engagement = DIMENSIONS.rear_pcb_screw_length - (
        DIMENSIONS.carrier_thickness + DIMENSIONS.rear_clearance + DIMENSIONS.pcb_thickness + DIMENSIONS.rear_pcb_washer
    )
    front_engagement = 5 - DIMENSIONS.lens_holder_thickness
    assert rear_engagement >= 2.0, "Insufficient PCB screw engagement"
    assert rear_engagement + front_engagement < DIMENSIONS.lens_standoff - 0.25, "Opposing screws bottom out"
    assert solid_volume(mount.intersect(guard())) < 1e-5, "Carrier collides with guard"
    return {"valid": True, "carrier_volume_mm3": round(solid_volume(mount), 2),
            "pcb_hole_pitch_mm": [17.78, 45.72], "pcb_supports": 4}


if __name__ == "__main__":
    import json

    print(json.dumps(verify_mount(), indent=2))