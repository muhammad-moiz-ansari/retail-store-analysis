# Eight-camera retail CCTV test footage

Open **security_monitor_8cams.mp4** for an NVR-style security-office display.
Eight independent files **cam01.mp4** through **cam08.mp4** are available for
the analysis pipeline. Each feed is 960 x 540, 10 FPS, 60 seconds.
They use H.264/yuv420p, frame-aligned timestamps, no audio, no camera time offset.

## Map interpretation

The supplied unlabeled map is interpreted as a 16 x 9 m open-plan store:
eight colored peripheral zones surrounding the black shared aisle. Color
regions indicate camera zones, not solid room partitions. Two small magenta
marks at the left are assumed to be entrances. Camera mounts, shelves and
door meanings are assumptions because the reference has no legend or view
arrows. See reference_map.png and layout_preview.png.

CAM01 pink upper left: entrance/produce; CAM02 tan upper middle: grocery;
CAM03 gray upper right: chilled; CAM04 yellow middle right: right aisle;
CAM05 red lower right: household; CAM06 cyan lower middle: checkout;
CAM07 purple lower left: lower entrance; CAM08 pale yellow middle left: left aisle.

## Shared scenario and employee colors

8 employees wear orange vests with silver reflective strips and dark trousers.
12 customers wear other clothing colors. Every person has one deterministic
world-space trajectory, used by every camera, so identities and movements are
consistent across overlapping views. Employee/customer pairs face one another
and gesture at 19-30 seconds; other customers enter, cross the center and exit.
The monitor's ninth tile shows the same live positions on the supplied layout.

## Testing and labels

Use the individual feeds for inference; the monitor grid is for human review.
A COCO-pretrained YOLO model predicts `person`, not `employee` from uniform
color automatically. Test a person detector plus an orange-region check on
torso crops, or train a custom two-class employee/customer detector. The color
convention applies to this fixture only. Person detection accuracy on these
procedural human models is not guaranteed.

manifest.json contains cameras, shared clock, resolution and assumptions.
actors.json contains persistent synthetic IDs, roles, colors and trajectories.
observations.jsonl contains one record per camera/frame with depth-tested
visible person boxes, visible pixel counts, facing and world positions.
events.json contains eight scripted engagement intervals. preview_*.jpg are
decoded frames from the final monitor file. verification.json records final
file checks. No real-world accuracy or training sufficiency is claimed.

## Regenerate

Requirements: Python 3.12+, numpy, pillow, moderngl, glcontext, and ffmpeg.
On Linux/WSL install the Python packages in a separate virtual environment;
the renderer uses a headless EGL context and works with Mesa software OpenGL.

`python generate.py --output ./rerender --duration 60 --fps 10`

Use a new output directory: the generator intentionally refuses to replace
an existing recording. Source time starts at 2026-10-04 10:00:00 Asia/Karachi.
