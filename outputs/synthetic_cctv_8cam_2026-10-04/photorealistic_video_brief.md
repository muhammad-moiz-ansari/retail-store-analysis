# Photorealistic eight-camera retail CCTV brief

## Required result

One 60-second store scenario, captured simultaneously by eight fixed CCTV
cameras, each covering ONLY ONE assigned colored zone, delivered as eight
individual camera MP4s plus an NVR monitor composite.
Photorealistic people, clothing, product shelves, materials and lighting are
required. No cartoon figures, mannequins, game-like materials or stylized rendering.

## Reference layout and assumptions

Use reference_map.png as the authoritative geometric reference. The eight
colored peripheral areas correspond to eight camera zones. The black middle
area is provisionally interpreted as an open circulation hub. The two small
magenta marks along the left edge are provisionally interpreted as doors.
These meanings are assumptions because the supplied map contains no legend.
The colored boundaries describe regions, not solid internal dividing walls.

Camera zones, numbered clockwise from the upper left:

1. Pink, upper left: entrance and produce.
2. Tan, upper middle: groceries.
3. Gray, upper right: chilled goods.
4. Yellow, middle right: right aisle.
5. Red, lower right: household goods.
6. Cyan, lower middle: checkout.
7. Purple, lower left: second entrance.
8. Pale yellow, middle left: left aisle.

Use ceiling-mounted CCTV cameras with fixed poses, ordinary overhead fluorescent
lighting, slight CCTV compression and realistic perspective. Frame or crop each
feed so it shows ONLY its assigned zone: no adjacent zones or whole-store views.
Do not give multiple cameras the same assigned zone. The black central aisle is
an unrecorded transit area unless the user changes its assignment. Each camera
may show people only while they are in its assigned zone; cut off out-of-zone
pixels at the frame boundary. No cinematic camera movement, zooms, cuts, dramatic lighting,
depth-of-field blur, or handheld shots. Individual feeds should be 960x540 or
higher, at a common constant FPS and with the same source duration.

## People and timeline

Employees wear bright orange vests with silver reflective strips and dark
trousers. Customers wear blue, green, purple, burgundy, teal, off-white or gray
clothes; no customers wear the employee uniform. Keep each individual's face,
hair, body, clothing, location and movement continuous across all camera views.

People enter at the left doorways, browse shelves and cross the central aisle.
At 19-30 seconds, employees and customers engage in visible conversations:
close proximity, mutually facing bodies, natural arm gestures. Other shoppers
walk past, providing negative cases. At 30-60 seconds conversations end,
customers walk toward checkout or an exit and staff return to their aisles.

## Synchronization requirement

All feeds represent one shared event, not eight independent store scenarios.
At source time t, every person's location follows one global trajectory. A
person leaving one zone can appear in another camera only after reaching that
camera's zone, retaining the same face, clothes and movement continuity. Their
transit across the black central aisle creates an expected visibility gap.
Each feed covers exactly one zone; synchronization does not require overlapping
views. A common timestamp alone does not satisfy cross-zone movement consistency.
If a generator cannot preserve shared geometry and actor movement, identify
the output as a visual demo and do not claim cross-camera synchronization.

## Monitor composite

Create a 1920x1080 security-office NVR display: eight CCTV feeds in a 3x3 panel
layout, with the ninth panel showing the reference floor plan. Camera names,
recording indicators and timestamps are added after generation so they are
legible and synchronized. The view is the monitor's displayed footage, not a
photo of an office or a security guard looking at screens.

## Verification before delivery

Verify equal duration, frame counts, FPS, and timestamps. Review cross-zone
handoffs against the shared source timeline to check actor identity, layout and
movement; verify each frame contains only its assigned zone.
Test the existing person detector on each view and inspect vest-color crops.
Pretrained YOLO detects persons; role-by-color needs a separate torso-color
rule or a trained uniform/role classifier. Do not claim successful detection
or real-world accuracy without running the checks.

## Current capability dependency

A photorealistic video generator has not been connected. Runway was found in
plugin discovery and suggested to the user. Its specific connected tools and
ability to preserve eight-view consistency must be inspected after connection.
The current stylized draft is superseded and is not a final deliverable.
