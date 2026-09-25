# Mechanical Sources And Assumptions

Checked against manufacturer pages and source files on **2026-09-25**.
Dimensions are millimeters. Source-derived dimensions are distinguished from
design clearances and unmeasured assembly assumptions.

## Manufacturer References

| Part | Source facts used | Reference |
| --- | --- | --- |
| HalloWing M0, #3900 | Nominal 60 x 51 x 11 envelope; rear LiPo/USB ports; USB upward | [Guide](https://learn.adafruit.com/adafruit-hallowing/overview), [product](https://www.adafruit.com/product/3900), [downloads](https://learn.adafruit.com/adafruit-hallowing/downloads) |
| LiPo #1578 | 29 x 36 x 4.75; 102 mm lead; 500 mAh, 3.7 V nominal | [Adafruit battery](https://www.adafruit.com/product/1578) |
| Glass lens #3853 | 40 outer diameter, 37.5 inner/dome diameter, 16 height, 22 focal length; lip-edge retained by holder | [Adafruit lens](https://www.adafruit.com/product/3853) |
| Lens holder #4013 | 52.3 x 50 x 2.8 nominal; eight M2.5 x 5 screws and four M2.5 x 6 F-F spacers | [Adafruit kit](https://www.adafruit.com/product/4013) |
| Lens assembly | Acrylic and PCB joined by four nylon M2.5 spacers and eight screws | [Adafruit assembly guide](https://learn.adafruit.com/hallowing-all-seeing-skull/build-the-all-seeing-skull) |
| Prusa CORE One+ | 250 x 220 x 270 build volume; one nozzle without MMU/INDX | [Prusa CORE One+](https://www.prusa3d.com/product/prusa-core-one/) |

The battery listing notes a folded/taped cable-end change from June 2022. The
cradle therefore has more room than the nominal pouch dimensions and uses a
soft strap rather than a tight clip. Check your particular battery, including
its end seal and cable fold; the cavity is not permission to use a swollen cell.

## Verified Hole Geometry

Source repository: [Adafruit-Hallowing-M0-PCB](https://github.com/adafruit/Adafruit-Hallowing-M0-PCB),
pinned at commit `c0585b0672ce13e163b8da6ce9215ec600c63d64`.

The Eagle board contains two plain 2.54 mm lower lens holes at
`(X,Y) = (+/-8.89, -18.161)` and two plated 2.5 mm upper lens holes at
`(+/-8.89, +27.559)`. Thus the pitch is **17.78 x 45.72**. The two larger
3.175 mm lanyard holes at `(+/-17.145, +22.86)` are **not** used by this design.

The lens-holder Illustrator file is a PDF-compatible vector drawing. Reading
its actual hole subpaths gives the same 17.78 x 45.72 pitch. Its central lens
circle maps to approximately `Eagle Y = 3.082925`, which is **1.616075 mm below**
the four-hole pattern's midpoint. The model uses that center, with +/-2 mm
vertical adjustment through the bucket's separate M2 carrier fasteners.

The historical vector drawing's aperture is approximately **36 mm**, while the
current glass listing mentions a **38 mm mounting cutout**; its outside outline
also differs slightly from the current kit's nominal dimensions. Accordingly,
**this project does not recreate or replace the acrylic retainer**. It reuses
the purchased kit and provides a 44.4 mm clearance opening in the bucket for the
40 mm lens. Validate the actual kit revision on the coupon.

The manufacturer notes an October 2023 PCB silkscreen/connector update; the
published mechanical source is older. No claim is made that a later unmeasured
revision is mechanically identical. The M0 hardware must pass the fit test.

The structured measurements, source hashes, connector locations, and PCB outline
are recorded in [hardware_reference.json](hardware_reference.json). The original
board and acrylic design are by **Limor Fried/Ladyada for Adafruit Industries**;
their source repository publishes them under Creative Commons Attribution/Share-Alike.
See its [license](https://github.com/adafruit/Adafruit-Hallowing-M0-PCB/blob/master/license.txt).
The bucket and large cyclops skull artwork here are newly drawn, not a copied
third-party printable model. Original source files remain in an ignored cache,
not in the distributed manufacturing files.

To reproduce the source measurements from the repository root:

```sh
curl --fail --location --create-dirs 'https://raw.githubusercontent.com/adafruit/Adafruit-Hallowing-M0-PCB/c0585b0672ce13e163b8da6ce9215ec600c63d64/Adafruit%20Hallowing%20M0%20Express.brd' -o .cache/hallowing.brd
curl --fail --location --create-dirs 'https://raw.githubusercontent.com/adafruit/Adafruit-Hallowing-M0-PCB/c0585b0672ce13e163b8da6ce9215ec600c63d64/HalloWing%20Lens%20Holder.ai' -o .cache/lens-holder.ai
.venv/bin/python tools/inspect_hardware.py .cache/hallowing.brd --lens .cache/lens-holder.ai --output docs/hardware_reference.json
```

## Chosen Clearances And Unverified Items

- PCB thickness **1.6**, rear support height **12**, and a **1 mm insulating
  washer** are stack-up assumptions/design choices. Confirm actual thicknesses,
  component heights, and that the opposing M2.5 screw tips do not bottom out.
- The assembly has generous lateral clearance for the approximately 52 mm
  acrylic, PCB, and rear headers. The USB top throat is **22 x 23**, not a
  manufacturer-specified USB plug envelope. Try your actual plug before printing
  the full bucket. The switch/reset require removing the candy guard.
- The glass's complete lip cross-section and assembled focal behavior were not
  measured. The hole clears its full outer diameter; the purchased kit sets the
  display-to-lens spacing. Do not interpret the textured render dome as an
  optical simulation.
- Printed M2 and M2.5 clearances are **2.4** and **2.9** respectively. M2 nut
  recesses allow approximately **4.3 across flats / 1.8 deep**; the bucket-side
  sliding pockets have additional vertical room. These are FDM fit allowances,
  not ISO dimensions for the hardware itself.
- Battery space is **33 W x 42 H x 8.5 D**. The cell requires a soft pad,
  noncompressive strap, lead slack, and inspection before each use.
- Rope anchors are modeled 10 thick around 13 bores, tied into the black wall
  below the rolled rim. Their common Y = -16.66 axis comes from the complete
  installed assembly's nominal center of mass, not the geometric centerline.
  **No FEA, drop test, creep test, or physical carrying-load test** has
  been performed. Printed layer adhesion and rope abrasion must be evaluated.
- Density limits of **1.30 g/cm3 black / 2.00 g/cm3 glow** are conservative
  budgeting assumptions, not specifications for an unspecified filament brand.
  Actual slicing and manufacturing still control spool use.

## Cauldron Balance Assumptions

The CORE One+ version has a 224 mm belly, 200 mm height, 186 mm neck diameter,
8 mm rolled lip, and 146 mm flat base. The flat electronics face is at Y = -89
and the eye at Z = 125. The original skull silhouette is scaled to 90%, but
the eye bore and electronics interfaces retain their full-size dimensions.
The 3 mm skull now prints separately and attaches with four M2 x 10 screws;
the former 0.9 mm inlay has been removed, leaving a full-thickness black wall.
There are no moon or hat ornaments.

Nominal balancing uses black/glow densities of 1.24/1.50 g/cm3. PCB and battery
masses come from Adafruit; the glass is **estimated at 31 g** from its approximate
glass-cap envelope, not a measured product weight. The acrylic/kit (5 g), extra
carrier/guard fasteners (12 g), skull fasteners (3 g), strap/pad (3 g), and
component mass centers are estimates.
See [assembly and balance](ASSEMBLY.md#rope-balance) for the complete assumptions,
centered-candy scenarios, density/lens sensitivity, and required hanging test.

The computed nominal center is approximately (0, -16.66, 99.73). The two bore
centers at (+/-99.33, -16.66, 178) balance the empty assembly, not every possible
load. Both lug material and material removed by the offset holes are included
in the iterated balance solution. The coupon and discarded printing supports
are excluded. A symmetrically installed rope is assumed; unequal knots or
an off-center grip are not modeled.

## Digital Verification

[validation.json](validation.json) records valid CAD solids, watertight,
consistently wound meshes, volumes, bed envelopes, nonintersecting material
volumes, mounting/candy-guard clearances, fastener passages, and the coupon's
identity to the corresponding cauldron geometry. The black body and separate
flat glow faceplate are individually connected, nonintersecting solids. Four
additional screw bores, washer-bearing lands, and clearance for internal M2
hardware are checked. The actual faceplate is reused for the black coupon test.

Mass calculations use adaptive, spline-span CAD integration and are checked
against fine triangle meshes for both volume and centroid agreement. The
cauldron profile uses local cubic segments to avoid unstable section Booleans
on a single long interpolated surface. Checks require the coupon to retain a
complete wall, clear rope bores on the computed axis, uninterrupted lug bearing
rings, and support-critical bowl/neck slopes above 55 degrees.

[slicer_validation.json](slicer_validation.json) records native **PrusaSlicer
2.9.6** imports, per-object bounds, extruder **1 only**, five successful slices,
and the G-code audit. The audit examines executable commands, not the commented
settings footer, and checks model/nozzle/firmware notices, cleaning and levelling,
single-nozzle use, PLA temperatures, flow limits, all model-phase moves, and
heater shutdown. Four negative tests inject an extra tool, out-of-bed move,
overtemperature, and missing mesh activation; all must be rejected.

## Official Machine Profile

Source: [PrusaSlicer-settings-prusa-fff](https://github.com/prusa3d/PrusaSlicer-settings-prusa-fff),
commit `65c5c8f1e1c3836f306119c49d717759cbc368db`, bundle **PrusaResearch 2.5.10**.
The [pinned bundle](https://raw.githubusercontent.com/prusa3d/PrusaSlicer-settings-prusa-fff/65c5c8f1e1c3836f306119c49d717759cbc368db/PrusaResearch/2.5.10.ini)
and [PrusaSlicer 2.9.6 release](https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.6)
are the reproducible inputs. The executable used here is the official portable
Windows 2.9.6 build through WSL interop, not the earlier Linux 2.7.2 audit binary.

Profiles are resolved from **Prusa CORE One HF0.4 nozzle**, **0.20mm STRUCTURAL
@COREONE 0.4**, and **Generic PLA @COREONE HF0.4**. The official `start_gcode`
and `end_gcode` are preserved byte-for-byte at the configuration level. The
printer script emits COREONE identification, 0.4 mm high-flow nozzle checks,
the 6.8.1+16182 firmware notice, cleaning, mesh probing, chamber control, purge,
and parking. The glow profile sets `filament_abrasive=1`, activating the
firmware's abrasive/nozzle check. The original startup purge intentionally uses
Y = -2.5; model-phase motion is separately checked against the 250 x 220 bed.

Derived settings use seven walls, 0.20 mm layers, conservative 6/3 mm3/s black/glow
flow limits, and **220/215 C nozzle, 60 C bed** PLA temperatures. These are chosen
assumptions, not verified settings for an unspecified filament brand. Full
configuration files and input/output hashes are in
[profiles/provenance.json](../profiles/provenance.json). Prusa profile authors
and licensing remain with their source repositories.

The G-code is ready only for the explicitly documented **CORE One+ / 0.4 mm
wear-resistant high-flow / PLA / smooth PEI** setup. The user could not confirm
machine, nozzle, filament, or firmware details. It is **not a universal drop-in
file for all CORE One+ configurations**. Verify the setup and do not bypass
mismatch warnings. No printer connection was made, no firmware was changed, and
no physical manufacturing or carrying-load test was performed.