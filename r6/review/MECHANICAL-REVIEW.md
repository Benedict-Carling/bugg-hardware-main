# Mechanical and local-layout review

*This review was an AI-assisted review pass, separate from the passes that produced the design; it is not an independent human engineering review.*

Review date: 28 September 2026. Geometry was read from native KiCad files and
compared with the vendored public r5 board. This review did not write the PCB,
schematic or project; the identified fixes were applied afterwards.
Final electrical release checks are recorded separately in the final DRC, ERC
and CAD-verification reports.

The local-layout snapshot reviewed here has SHA-256
`4096fc0274215e49849a9bc573aa944843365a8ca247d04ec7523652dada04db`.
Subsequent signal routing must pass the final native checks again.

## Preserved interfaces

The enhanced `design/verify_board.py` passed its separate run: all 37 recorded
fixed interfaces matched r5 in position, rotation, board side and pad mechanics.
These include connectors, the CM4 interface, SIM and battery holders, mounting
holes, enclosure bosses, ground contacts and fiducials. Board-outline primitives
are unchanged; the board remains six copper layers and 1.6 mm thick.

All 59 original test points remain, with no added test points or buttons. Original
USB and microphone-input traces and vias match r5 exactly, including widths,
endpoints, drill sizes and layer spans. A segment of the existing low-speed I²C
SDA bus is rerouted to accommodate a ground stitch; it is not part of either
protected differential pair.

The verifier now asserts the microphone-input and USB comparisons and rejects
a run if the PCB changes during verification. Its final run must use a freshly
exported schematic netlist. The earlier run checked 493 footprint
references/values and 1,826 pad-to-net assignments successfully.

## Physical clearance findings

Moving C142 to `(-25, -14.75)` and C150 to `(26.8, -18.5)` resolved the
C142/C143 and U40/C150 courtyard overlaps. Moving C144 to the back side at
`(-10, -29.6)`, rotation 0°, removed its overlap with the SIM-holder courtyard.
The final local scan includes added and modified footprints on both sides.

One specific courtyard exception is retained: C144 overlaps the access courtyard
around original test point T9 by 0.280 mm². T9 is a bare 1 mm copper test pad,
not a component body. The modeled capacitor body is **0.55 mm from the test-pad
copper edge**, and the pad remains exposed. T9 itself is unchanged. This is an
accepted probe-access margin exception, not a physical component collision;
native copper-clearance checks still apply. No other new or modified-footprint
courtyard overlap was found.

## Bypass routing and ground returns

The review found a 10.27 mm supply-trace detour between U38 and its bypass
capacitor in an intermediate r6 layout. The back-side C144 placement replaces
it with **1.70 mm of horizontal trace and one through-via**. This is a correction
within the r6 development work, not a performance comparison against r5.

| Circuit | Bypass capacitor | Supply-trace length | Nearest GND-via center distance from capacitor ground pad |
| --- | --- | ---: | ---: |
| U37 input | C142 | 2.45 mm | 0.89 mm |
| U37 output | C143 | 2.90 mm | 0.80 mm |
| U38 telemetry ADC | C144 | 1.70 mm | 2.40 mm |
| U39 I²C expander | C149 | 1.53 mm | 0.65 mm |
| U40 latch | C150 | 1.51 mm | 0.72 mm |
| U41 logic buffer | C151 | 1.95 mm | 1.30 mm |

Supply lengths are measured along the routed horizontal copper; vertical travel
through vias is additional. GND-via distances are geometric distances, not
measurements of impedance or the complete return-current path. C144's ground
pad joins the back-side ground pour. The other five listed capacitors received
nearby ground vias, shortening previously distant returns, particularly at
C142, C143 and C149.

The D20 front-side ground region received a stitch to the main inner ground
plane. Subsequent signal routing exposed two places where a poured-copper
connection could be split again. These received explicit pad-to-plane routes:

- U35.2 and C120.1 are joined by a back-side ground trace, with C120.1 explicitly
  routed to the existing main-plane ground via at `(-8.55, -27.4)`.
- R218.2 has an explicit front-side ground trace to a main-plane ground via at
  `(-9.25, -38.96)`.

These connections no longer rely on a narrow pour neck remaining intact when
neighboring signal routing changes. The authoritative final ground-connectivity
and clearance result is `final-drc.json`; earlier intermediate checks are not
substitutes for that final run.

These changes remove avoidable routing defects and reduce local bypass-loop
length. They do not establish measured supply noise, ADC accuracy, audio
self-noise or EMC performance. There was no physical prototype or audio
measurement in this review. Enclosure tolerances, assembly and electrical
performance still require prototype validation.
