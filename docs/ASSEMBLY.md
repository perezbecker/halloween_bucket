# Cyclops Cauldron Assembly

Assemble and test the small wall section before printing the full bucket.
The skull, carrier, guard and electronics from that test are reused in the
finished cauldron. White and glow skulls have identical geometry and hardware.

A completed build has been reported to work well. Printer tolerances and
hardware revisions can vary, so check your own parts rather than forcing a
fit. Use the HalloWing **M0**, not another board model.

[Hardware](#hardware-list) | [Illustrations](#illustrated-assembly-sequence) |
[Fit test](#fit-test-first) | [Final assembly](#final-assembly-and-use) |
[Mechanical reference](#mounting-datums)

## Hardware List

| Quantity | Item | Purpose |
| ---: | --- | --- |
| 1 | Adafruit #3900 HalloWing M0 | Eye display and controller |
| 1 | Adafruit #3853, 40 mm glass lens | Convex eye |
| 1 | Adafruit #4013 acrylic lens-holder kit | Acrylic, four 6 mm M2.5 F-F standoffs, and four front M2.5 x 5 screws |
| 1 | Adafruit #1578, 3.7 V 500 mAh LiPo | 29 x 36 x 4.75 mm nominal battery |
| 4 | **M2.5 x 20 mm** machine screws | Through the carrier, printed PCB posts and PCB into the kit standoffs |
| 4 | **1.0 mm thick M2.5 insulating washers**, outside diameter <=6 mm | Under the long rear screw heads, against the carrier |
| 4 | **M2 x 20 mm** machine screws | Bucket/coupon to carrier |
| 4 | **M2 x 20 mm** machine screws | Candy guard to carrier |
| 4 | **M2 x 10 mm** machine screws | Skull to the black wall |
| 12 | M2 hex nuts, approximately 4 mm across flats and 1.6 mm thick | Eight in carrier recesses; four loose inside the wall for the skull |
| 12 | M2 washers, approximately 0.5 mm thick, outside diameter <=5.5 mm | Spread head loads on the bucket, guard and skull |
| 1 | Soft hook-and-loop strap, 8-10 mm wide and <=2 mm thick, about 120 mm long | Loosely retain the battery through the guard slots |
| 1 | Thin, soft, electrically insulating pad, approximately 1 mm thick | Cushion the battery against the guard back |
| As needed | Nylon sail rope, approximately 8-10 mm diameter | Handle with two stopper knots inside the pail |

Total separate screws: **eight M2 x 20**, **four M2 x 10**, and **four M2.5 x 20**.
Keep the kit's four front M2.5 x 5 screws; its short rear screws are not used
through the printed carrier.

**M2 and M2.5 are different threads.** Do not substitute M2 screws in the
lens-kit standoffs. Prefer nonconductive hardware around the PCB. If using
metal screws, check clearances from components and exposed conductors.
Do not use pointed self-tapping screws, drill the PCB, or force screws into
printed plastic.

## Prepare The Eye Electronics

This project supplies the mechanical housing, not custom firmware. The
[Adafruit HalloWing M0 guide](https://learn.adafruit.com/adafruit-hallowing/overview)
describes the board and its default spooky-eye demo. Check that the board
powers up and displays the eye before installing it; use Adafruit's M0
documentation if it needs software setup or troubleshooting.

Keep the USB connector pointing upward. Use the purchased acrylic lens
holder, its four **6 mm M2.5 standoffs**, and four **front M2.5 x 5 screws**.
The acrylic kit retains the glass lip; **the printed eye opening does not
press-fit, clamp or support the glass**.

Disconnect power before mechanical work. Use the intended LiPo connection,
verify polarity, and keep the battery away from tools and screw paths.
The repository's USB G-code files are for the 3D printer, not the HalloWing.

## Illustrated Assembly Sequence

The six cards correspond to the detailed fit-test steps below. Open an image
for its full-resolution numbered callouts. Printed parts come from the STL
meshes; electronics, fasteners, strap, rope and optics are illustrative.
Exploded gaps and arrows are not to scale. Hardware colours distinguish screw
groups, not print materials. The illustrations show a glow-coloured skull;
the white version assembles the same way.

![Six assembly cards](../renders/assembly/overview.png)

### 1. Skull To Test Wall

Four **M2 x 10 screws**, outside washers and loose nuts inside the wall attach
the skull. Its other four large openings provide access to the carrier screws.

![Attach the skull to the test wall](../renders/assembly/01_skull_to_wall.png)

### 2. Lens, PCB And Carrier

Four **M2.5 x 20 screws with 1 mm insulating washers** pass through the carrier,
its PCB support posts and the PCB into the kit standoffs. Keep USB upward.

![Build the lens and PCB module](../renders/assembly/02_lens_and_carrier.png)

### 3. Carrier To Wall

Four **M2 x 20 screws** enter from outside. Seat their nuts at the bottoms of
the **15.9 mm deep rear rectangular wells**, not at the openings. Start loosely,
adjust eye alignment within +/-2 mm, and check glass clearance before tightening.

![Mount and align the carrier](../renders/assembly/03_carrier_to_wall.png)

### 4. Battery Pad And Strap

Fit the battery in the guard while it lies flat. Use the insulating pad and
soft strap through both slots; retain the pouch without squeezing it.

![Pad and strap the battery](../renders/assembly/04_battery_and_strap.png)

### 5. Removable Guard

Four nuts in the carrier's **front hex recesses** receive the guard's
**M2 x 20 screws and washers** from the candy side. Inspect wire routing and
USB access before closing the guard.

![Fit the removable guard](../renders/assembly/05_close_guard.png)

### 6. Transfer And Hanging Checks

Move the tested parts to the full cauldron, install the rope through its bores,
and secure substantial inside stopper knots with adequate tails. The knot
markers in the illustration are schematic, not knot-tying instructions.

![Transfer the parts and check the rope](../renders/assembly/06_rope_and_final_checks.png)

## Fit Test First

1. Print [the test wall](../print/01_mount_test_black.3mf),
   [one skull](../print/02_skull_faceplate_glow.3mf), and
   [the combined carrier/guard plate](../print/03_04_carrier_guard_black.3mf)
   or the individual [carrier](../print/03_carrier_black.3mf) and
   [guard](../print/04_guard_black.3mf). Follow the material choices and
   printer prerequisites in [PRINTING.md](PRINTING.md).
2. Remove supports and burrs from the eye opening, mounting holes, nut wells
   and PCB support faces. M2 screws should pass freely through 2.4 mm passages,
   and M2.5 through 2.9 mm passages. Enlarge only printed plastic if necessary,
   with all electronics and the battery removed.
3. Attach the skull to the empty test wall with **four M2 x 10 screws**, washers
   on the skull side, and loose nuts inside the wall. The holes are at
   X = +/-30, Z = 80 and 165. Use the recessed **3 mm thick seats with 8.4 mm
   diameter lands**, not the larger carrier-access openings. Tighten gently
   until the flat back meets the wall without bending. A 0.5 mm washer,
   3 mm skull seat and 3 mm wall leave about 3.5 mm of screw for the nut and
   tip. Confirm real hardware lengths before installing electronics.
4. Check that all four PCB post centers match the real board without bending
   it, and that rear components clear the carrier. Stop if the board revision
   differs. Trial-fit the bucket screws and deep-well nuts before adding the
   PCB. Also preload the guard nuts into the front hex recesses; a small piece
   of tape can hold them temporarily.
5. Assemble the lens and acrylic with the stock standoffs and front M2.5 x 5
   screws. Rest the PCB on its four printed posts. From the rear, install the
   **four M2.5 x 20 screws and 1 mm insulating washers** through the carrier,
   posts and PCB into the standoffs. Check the [screw engagement](#side-stack)
   by hand, and tighten only enough to locate the board.
6. Seat four M2 nuts at the **bottoms of the 15.9 mm deep rear rectangular
   wells**. Their flats fit between the 4.3 mm wide side walls; the 8.8 mm
   height permits vertical adjustment. With the long posts pointing down,
   gravity, tweezers or a narrow blunt tool can help seat the nuts. Do not
   hammer them in. Loosely connect the carrier to the wall using
   **four M2 x 20 screws and 0.5 mm washers** from outside. All four should
   engage the metal nuts without bottoming or pulling the posts sideways.
7. Slide the carrier vertically until the eye is centered and the glass clears
   the printed opening all around. Check that the acrylic and its screw heads
   do not touch the wall. Do not use screws to pull glass through a tight hole.
8. Power the board and inspect eye centering, focus, oblique viewing and light
   leaks. The kit fixes the lens-to-display spacing; moving the carrier moves
   the complete module. Switch off and disconnect power before continuing.
9. Check that the battery sits loosely in the **33 x 42 x 8.5 mm bay**,
   including its folded/taped end and pad. Thread the strap through both
   **2.6 x 11 mm slots** and retain the battery without compressing the pouch.
10. Check that the four guard nuts are seated in the carrier's front hex
    recesses. Connect the battery with slack in its lead, then attach the
    guard from the candy side with **four M2 x 20 screws and washers**.
    No lead may cross a screw path or be trapped under an edge.
11. Check the USB plug through the **22 x 23 mm top opening** and confirm the
    guard can be removed without disturbing the lens. Access the battery
    connector, switch and reset button with the guard removed.

The coupon's foot supports the bare **wall + PCB + carrier** test. The full
skull and guard extend below it: hold the assembly above a padded surface or
bench edge while fitting them. Check the battery bay with the guard lying flat.
This small fixture is not a whole-bucket strength or balance test.

Record hole fit, glass clearance, acrylic thickness, alignment and battery
clearance before committing to the full print. Reuse these tested parts and
hardware in the finished bucket.

## Final Assembly And Use

Print the cauldron and follow the same assembly sequence on its front wall.
Deburr the two **13 mm rope holes**, thread the handle through them, and secure
substantial stopper knots inside. Leave adequate tails, check that the knots
cannot pull through, and use equal-length rope legs. No printed handle is
included.

Complete the [hanging check](#rope-balance) before use. There is **no certified
load rating**. After the empty check, begin with a **1 kg static test load**
just above a soft surface and inspect the bosses and layer lines. This is a
test procedure, not a rated capacity; establish suitability for the intended
contents with controlled testing. Stop at flexing, cracking or layer separation.
Do not swing a loaded bucket or use its rope as a neck strap.

Use wrapped candy or a removable food-safe liner. Printed PLA/glow filament
and layered FDM surfaces are not represented as food-contact safe. The guard
is a candy shield, not a sealed, waterproof, impact-proof or fireproof enclosure.
Protect the glass from impacts; it can break if dropped.

Switch off and empty the bucket before servicing. Charge under supervision in
an open, nonflammable location, preferably with the electronics removed and
guard off, never under candy. Do not use a swollen, damaged, crushed or hot
LiPo. Verify connector polarity, keep screw tips away from the pouch, and do
not overtighten the strap. Avoid heat, hot cars and rain.

## Rope Balance

Hang the empty assembly just above padding and check the rim from the front
and side. Repeat with the intended candy load distributed evenly. Inspect
the anchors and knots before carrying. Do not drill or elongate holes through
the thin body wall to alter balance.

The bore centers are **(-99.33, -16.66, 178)** and
**(+99.33, -16.66, 178)** mm: both are 16.66 mm toward the electronics from the
geometric centerline, at the same height.

The [balance model](validation.json) uses nominal densities of **1.24 g/cm3
black** and **1.50 g/cm3 glow**, CAD volume centroids, and hardware estimates:
17.5 g PCB, 10.5 g battery, 31 g glass, 5 g acrylic/lens hardware, 12 g
carrier/guard fasteners, 3 g skull fasteners and 3 g strap/pad. These are not
measurements of the completed build. They differ from the conservative
densities used for filament budgeting.

For a glow skull, the nominal assembled mass is **864.9 g**, with its center
near **(0, -19.44, 100.59)** mm, about **77.4 mm below** the rope axis.

| Centered candy load | Predicted pitch |
| --- | --- |
| Empty, electronics installed | 2.1 degrees toward the eye |
| 500 g | 2.7 degrees away from the eye |
| 1,000 g | 4.5 degrees away from the eye |

The payload model places candy at (0, 0, 65) mm. A fixed pair of holes cannot
keep the rim level for every fill. Varying black/glow density and glass mass
gives about -4.4 to -0.6 degrees of empty pitch; it does not bound uneven
packing, rope or all hardware differences. **White PLA changes the skull mass
and balance**, so use the physical hanging check for that build too.
Measured masses can be entered in the [parametric model](../design/bucket.py);
changing balance assumptions does not reposition the modeled rope holes.

## Mounting Datums

This reference is for checking hardware or editing the CAD. Units are
millimeters. Viewed from outside: X is right, Z is up, and the flat mounting
face is Y = -89. The eye center is X = 0, Z = 125. USB points upward.

| Feature | X coordinates | Z relative to eye center |
| --- | --- | --- |
| PCB/lens-kit upper mounting holes | -8.89, +8.89 | +24.476 |
| PCB/lens-kit lower mounting holes | -8.89, +8.89 | -21.244 |
| Bucket-to-carrier M2 fasteners | -40, +40 | -35, +35 |
| Guard-to-carrier M2 fasteners | -41, +41 | -25, +25 |
| Skull-to-wall M2 fasteners | -30, +30 | -45, +40 |

The stock kit uses the **17.78 x 45.72 mm** hole pattern, not the larger
lanyard holes. In the published drawing, the lens center is approximately
**1.616 mm below the mounting-pattern midpoint**. The carrier's slots provide
+/-2 mm of vertical adjustment for the actual lens/PCB fit.

## Side Stack

From outside to inside, excluding screw heads:

1. Skull back Y = -89; 3 mm seating layer and screw seats at Y = -92.
   Contours reach approximately Y = -99.5. The eye bezel is at Y = -92;
   the black wall spans Y = -89 to -86.
2. Stock lens/acrylic assembly: nominal acrylic front Y = -82.5, back Y = -79.7.
3. Stock **6 mm M2.5 F-F standoffs**, between acrylic and PCB front.
4. PCB front Y = -73.7, rear Y = -72.1; nominal thickness 1.6 mm.
5. **12 mm printed PCB posts**, touching the board only around mounting holes.
6. **3 mm carrier plate**, front Y = -60.1, rear Y = -57.1.
7. 1 mm insulating washers and M2.5 x 20 rear screw heads.
8. Free space, then guard inner back Y = -45.5, outer back Y = -43.5.

The bucket-to-carrier stack is **0.5 mm washer + 3 mm wall + 13 mm post before
the nut + 1.6 mm nut = 18.1 mm**. An M2 x 20 screw projects approximately
**1.9 mm beyond the nut**, inside its well. The nut's bearing plane is
Y = **-73.0**, 15.9 mm forward of the carrier rear. The skull's large access
holes let these screw heads bear on the black wall, so skull thickness is not
part of this stack.

The PCB/lens stack assumes 2.8 mm acrylic. Rear M2.5 screws engage about
**2.4 mm** and front screws about **2.2 mm** into each 6 mm standoff.
**Their tips must not meet.** Check real acrylic, washer and screw dimensions
by hand; adjust insulating washers or screw length if necessary. Never
tighten a bottomed-out screw to pull parts together.

The 40 mm lens has a nominal 16 mm overall height; its exact lip seating depth
was not measured. The stock holder retains the lip, and the bucket clears
the full lens diameter rather than assuming a precise glass profile. Expect
the dome to protrude a few millimeters beyond the bezel, depending on the kit.
