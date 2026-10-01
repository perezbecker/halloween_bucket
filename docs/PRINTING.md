# Printing The Cyclops Cauldron

The bucket has four installed printed parts: body, skull, electronics carrier
and battery/candy guard. A small mounting-test wall checks the assembly before
the full bucket print. All parts use one filament per job and one extruder.

The design has been printed and reported to work successfully. Use the
following setup checks for your own printer and material, even when printing
the supplied files.

## Material And Printer Setup

The [USB jobs](../usb/COREONE_04HF_PLA/) are ASCII G-code from **PrusaSlicer
2.9.6**, based on the official **Prusa CORE One HF0.4 nozzle** machine profile
and PrusaResearch bundle **2.5.10**. The COREONE profile is used for the
single-tool CORE One+.

| Requirement | Configuration |
| --- | --- |
| Printer | Stock Prusa CORE One+, one tool, no MMU or INDX |
| Nozzle | **0.4 mm high-flow** |
| Filament | **1.75 mm PLA**, rated for **220 C first layer / 215 C thereafter** |
| Sheet | Clean smooth PEI suitable for PLA |
| Bed | **60 C** |
| Chamber | Official automatic control, nominal **20 C**; keep vents unobstructed |
| Firmware | Compatible with the official profile; G-code includes notice **6.8.1+16182** |

For glow PLA, also use a **wear-resistant/hardened nozzle** and filament rated
for its 0.4 mm bore. Ordinary white or black PLA does not require the abrasive
filament check.

**Do not bypass printer/nozzle warnings.** A standard-flow or different-size
nozzle, different printer, sheet or material requires the appropriate profile
and reslicing. Glow PETG, including Prusament PETG Ultraglow, is not PLA and
must not use these jobs.

Official startup cleaning, probing, chamber control, purge and shutdown are
preserved. The startup cleaning/purge path intentionally uses Y = -2.5 before
layer 1. Model-phase moves are separately checked against the
**250 x 220 x 270 mm** build volume.

## Choose The Jobs

Print **one skull**, in either white or glow PLA. Print **one carrier and one
guard**, either together or in separate jobs. These are alternatives, not
additional parts.

| Part or plate | G-code | Material estimate | Time estimate |
| --- | --- | ---: | ---: |
| Mounting-test wall | [01 Test](../usb/COREONE_04HF_PLA/01_test_BLACK_04HF_PLA.gcode) | 37.27 g PLA | 1 h 47 m |
| White skull | [02 White](../usb/COREONE_04HF_PLA/02_skull_WHITE_04HF_PLA.gcode) | 64.17 g PLA | 4 h 52 m |
| Glow skull | [02 Glow](../usb/COREONE_04HF_PLA/02_skull_GLOW_04HF_PLA.gcode) | 98.72 g glow PLA | 5 h 40 m |
| Carrier and guard together | [03+04 Combined](../usb/COREONE_04HF_PLA/03_04_carrier_guard_BLACK_04HF_PLA.gcode) | 109.53 g PLA | 5 h 17 m |
| Carrier only | [03 Carrier](../usb/COREONE_04HF_PLA/03_carrier_BLACK_04HF_PLA.gcode) | 26.20 g PLA | 1 h 32 m |
| Guard only | [04 Guard](../usb/COREONE_04HF_PLA/04_guard_BLACK_04HF_PLA.gcode) | 83.38 g PLA | 3 h 44 m |
| Full bucket | [05 Cauldron](../usb/COREONE_04HF_PLA/05_cauldron_BLACK_04HF_PLA.gcode) | 622.99 g PLA | 26 h 22 m |

Print the small parts and complete the [fit test](ASSEMBLY.md#fit-test-first)
**before printing job 05**. Reuse the same skull, carrier and guard in the
full cauldron. You may group the conventional-PLA jobs to reduce filament swaps.
The `BLACK` and `WHITE` filenames describe the intended colours; conventional
PLA in another colour is usable if it meets the same material requirements.
The GLOW job has distinct flow and abrasive-filament settings.

### White PLA Skull

The white skull uses conventional, non-abrasive PLA with a **6 mm3/s flow
limit**. It prints flat-back-down with **0.10 mm layers**, a 0.20 mm first
layer, **100% rectilinear infill**, seven perimeters and ten top/bottom solid
layers, without supports or brim. It does not glow.

The [white profile](../profiles/core_one_plus_0.4HF_white_PLA.ini) and
[audit](white_skull_validation.json) record the settings, source geometry and
G-code hashes. The exact time estimate is **4 h 52 m 26 s**.

### Glow PLA Skull

The glow skull has the same geometry, mounting holes, orientation and layer
settings as the white version. Its profile limits flow to **3 mm3/s** and
enables the abrasive-filament nozzle check. The estimate is **5 h 39 m 49 s**.
Check your filament's nozzle-size and temperature requirements before use.

### Combined Carrier And Guard

The [combined plate](../print/03_04_carrier_guard_black.3mf) contains the same
**M2 x 20 carrier** and complete guard as the individual jobs, in their
back-down orientations. Both print from one spool in one colour.

There is **15 mm XY separation** and at least **16.5 mm bed-edge clearance**.
The printer alternates between the parts on each layer: **144 layers print
both**, followed by **63 guard-only layers**, for 207 total. Sequential-object
printing is disabled; do not enable it when reslicing this layout.

The estimate is **109.53 g / 84.25 cm3 / 5 h 16 m 43 s**. Have approximately
**130 g available** for margin. The [combined-job audit](carrier_guard_validation.json)
checks source meshes, placement, tool assignments and the actual per-layer
extrusion sequence. Do not also run jobs 03 and 04 unless you want spares.

## Print From USB

1. Check the configuration above and the
   [USB checklist](../usb/COREONE_04HF_PLA/START_HERE.txt).
2. Copy the selected `.gcode` files onto a readable FAT32 USB drive and safely
   eject it. Do not format a drive containing needed data. The printer runs
   G-code, not a zip archive or the STL/STEP/3MF source files.
3. Clear the entire sheet, load the appropriate PLA through the printer's
   filament menu, insert the drive and select the job.
4. Check printer/nozzle/material notices. Watch automatic cleaning, levelling
   and the first layer; on the combined plate, inspect both parts. Stop if
   material lifts or extrudes poorly.
5. Let the sheet cool, remove the part and loose material, then prepare for
   the next job. Change filament **between jobs**, never partway through one.

No electronics, glass, battery or rope belong in the printer during a job.
There are no mid-print colour changes or purge towers.

## Supplied Settings

| Setting | Body, test wall, carrier and guard | Skull, white or glow |
| --- | --- | --- |
| Layer / first layer | 0.20 / 0.20 mm | 0.10 / 0.20 mm |
| Wall / first-layer extrusion width | 0.45 / 0.50 mm | 0.45 / 0.50 mm |
| Perimeters | 7 | 7 |
| Top / bottom solid layers | 8 / 10 | 10 / 10 |
| Nominal infill | 15% gyroid | 100% rectilinear |
| Brim | 5 mm on bucket and test wall; none on carrier/guard | None |
| Supports | Automatic organic supports enabled for bucket/test wall; off for carrier/guard | Off |
| Flow limit | 6 mm3/s | 6 mm3/s white; 3 mm3/s glow |

The cauldron's **3 mm walls, 3.6 mm floor**, rim and anchors are modeled
geometry. Do not scale them down or use spiral vase mode.

Infill percentage applies only to space left after perimeters and solid
layers. In the supplied combined carrier/guard job, those paths fill the
printed sections: **there is no sparse internal-infill toolpath**, despite the
nominal 15% setting. Designed holes, nut wells and the guard cavity stay empty.

## Plate Order

Keep the supplied orientations when reslicing:

| Geometry plate | Orientation and purpose |
| --- | --- |
| [01 Mounting test](../print/01_mount_test_black.3mf) | 116 x 28 x 103 mm wall section, upright on its rear foot; tests wall holes in the bucket's print orientation |
| [02 Skull](../print/02_skull_faceplate_glow.3mf) | Approximately 128 x 138 mm, flat back down, sculpted face up; up to 10.5 mm thick with 3 mm screw seats |
| [03 Carrier](../print/03_carrier_black.3mf) | Flat back down, posts up; the 15.9 mm rear nut wells open toward the bed |
| [04 Guard](../print/04_guard_black.3mf) | Outer back down, walls and battery cradle up |
| [03+04 Combined](../print/03_04_carrier_guard_black.3mf) | Both parts in the same orientations, side by side |
| [05 Cauldron](../print/05_cauldron_black.3mf) | Upright on its flat base, mouth up; print after fitting the small parts |

The skull STL/3MF names contain `glow`, but the geometry is shared by both
materials. Each plate is one material on extruder 1. The combined plate has
two separate objects on that same extruder.

[Individual print-bed previews](../renders/print_beds/overview.png) show the
five single-part plates at a common scale. Amber lines are brim/support
toolpaths, printed in the part's filament, not a second colour.

## Support And Preview Checks

The eye bore, rope bosses and rolled lip may need local supports. The bucket
and test-wall presets enable automatic organic supports; actual paths depend
on the geometry and slicing. Keep support and interface material on extruder
1 and accessible for removal. Do not fill the carrier's nut wells with support.

Inspect these areas in the slicer preview and after printing:

- **Skull:** flat back at Z = 0; relief up to about Z = 10.5 mm. The eye
  opening and all screw passages must be clear.
- **Bucket:** continuous perimeters around the rim and rope anchors; no
  inaccessible support around the eye opening.
- **Carrier:** four **4.3 x 8.8 mm rectangular wells, 15.9 mm deep**, ending at
  the narrower screw slots. Clear strings and trial-fit nuts to the bottoms
  before installing electronics. Check the M2.5 PCB passages too.
- **Guard:** clear screw passages, strap slots and USB opening.

Short bridges at the nut-pocket transitions and strap slots require a
calibrated material profile. Remove supports and burrs from all PCB support
faces; never leave plastic remnants pressing against a component or the glass.

## Filament Planning

The totals below include one bucket, one test wall, one carrier and one guard.
Add **one** of the skull choices.

| Job selection | Conventional PLA for body/test/carrier/guard | White skull | Glow skull |
| --- | ---: | ---: | ---: |
| Combined carrier/guard | 769.79 g | 64.17 g | 98.72 g |
| Separate carrier and guard | 769.84 g | 64.17 g | 98.72 g |

Sliced weights use conservative densities of **1.30 g/cm3 conventional PLA**
and **2.00 g/cm3 glow PLA**. They include automatic startup purge and emitted
brim/support material, but not manual loading, retries or extra copies.
These are estimates, not measurements of a printed build.

For the separate-job glow configuration, the [CAD budget](validation.json)
allows **905.86 g conventional PLA** and **148.41 g glow**, including reserves
of 125 g and 50 g respectively. A 1 kg spool per material is the design
budget, not a reason to begin a job without enough usable filament left.
Do not reduce wall or anchor strength to make a nearly empty spool last.

## Reslicing And Verification

For a different setup, load a geometry 3MF into PrusaSlicer, select the correct
official printer/nozzle/material profiles, retain the orientations and
mechanical wall thicknesses, and inspect the preview. Ordinary PLA and glow
PLA profiles are not interchangeable with PETG or other materials.

The [black](../profiles/core_one_plus_0.4HF_black_PLA.ini),
[white](../profiles/core_one_plus_0.4HF_white_PLA.ini) and
[glow](../profiles/core_one_plus_0.4HF_glow_PLA.ini) profiles document the supplied
settings. See [rebuild commands](../README.md#rebuild) to reproduce the files.

The [individual-job](slicer_validation.json),
[white-skull](white_skull_validation.json) and
[combined-plate](carrier_guard_validation.json) reports cover native import,
dimensions, tool assignments, machine limits and output hashes. The automated
checks are not physical load, impact or filament-certification tests.
