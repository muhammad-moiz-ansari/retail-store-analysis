# Backend summary

The interaction pipeline is built and benchmarked. It runs as a standalone tool and is not yet connected to the main backend. Two parallel designs exist side by side, and only one of them can run on real video. The frontend is out of scope for this document.

## 1. What the project is

RetailPulse turns existing store CCTV into analytics: whether customers get attended to, how staff spend their time, and where people go. The backend is Python (FastAPI, Ultralytics YOLO, OpenCV, SQLite). It has three areas:

| Area | Files | Purpose |
|---|---|---|
| **Interaction module** | `backend/interaction/` (~2,400 lines, 44 tests) | Detect and track people, label each as employee or customer, and find and confirm employee–customer interactions |
| **Camera handoff / identity** | `camera_handoff.py`, `handoff_core.py`, `camera_service.py` | Match the same person across two cameras and give them one anonymous global ID |
| **Store operations API** | `app.py`, `store_core.py`, `voice_agent.py` | Auth, settings, alerts, task dispatch, orchestrator events and voice announcements |

There are also some one-off scripts: `analyze_frame.py`, `compare_people.py` and `video_similarity.py`.

---

## 2. Interaction module (the main focus)

### 2.1 The question it answers

> "Is a staff member actually serving this customer right now, and for how long?"

It does this as a funnel. Each stage is cheap and filters the candidates before a more expensive stage runs:

```
frame ─► detect + track (1 model) ─► stable IDs (relink) ─► role per person (weighted agent)
      ─► proximity candidate (body-height distance + pass-by filter + min duration)
      ─► pose judge (are heads turned toward each other?) ─► confirmed / rejected interaction
```

### 2.2 Where each piece lives

| Stage | File | Key class / function |
|---|---|---|
| Config (all thresholds) | `config.py` | `InteractionConfig` |
| Orchestration | `pipeline.py` | `InteractionPipeline.process_frame` |
| Detection + tracking + ID memory | `tracker.py`, `botsort_reid.yaml` | `ByteTrackPersonTracker` |
| Role evidence per frame | `role_classifier.py` | `RoleClassifier` |
| Role decision (weighted agent) | `cust_emp_classifier.py` | `CustEmpClassifier` |
| Proximity + pass-by filter | `engagement.py` | `EngagementDetector`, `body_distance` |
| Second-model judge | `pose.py` | `PoseJudge`, `judge_frames`, `head_vector` |
| Output types | `types.py` | `TrackedPerson`, `InteractionEvent`, `CONFIRMED` |
| Video runner | `cli.py` | `analyse`, `main` |
| Overlay drawing | `renderer.py` | `draw_result` |
| KPIs | `benchmark.py`, `benchmarks/` | `detector_kpis`, `video_kpis`, `match_events` |
| Optional HTTP service | `service.py` | `POST /frame` on port 8012 |

### 2.3 Stage 1: one model for detection, tracking and role

- **What:** `backend/models/best.pt` is a custom YOLOv8 model trained on the store's bib-labelled CVAT data (notebook: `notebooks/train_staff_customer_yolov8_kaggle.ipynb`). It has two classes, `employee` and `customer`, and is exported to OpenVINO at 320 px (`best_320_openvino_model/`).
- **Why:** One model gives detection, tracking and the role signal in a single pass, at about 10 fps on a laptop CPU. A separate role model per frame would double the cost. OpenVINO only runs on CPU, so with `device="cuda:0"` the pipeline switches automatically to `best.pt` (`pipeline.py:293`).
- **Tracker:** The README says ByteTrack, but the actual config is **BoT-SORT with appearance re-identification (ReID)** (`botsort_reid.yaml`). Plain ByteTrack matches on position only, so when two people crossed, the ID jumped to the wrong person. The ReID features come from the detector itself (`model: auto`), so no extra model is needed.

### 2.4 Stage 2: ID memory (`tracker.py::_relink`)

BoT-SORT still loses people behind shelves or other shoppers. Two rules on top of it fix this:

1. **Hidden mid-frame, so give the old ID back.** Suppose a track disappears away from the left or right frame edge, and within `relink_seconds` (5 s) a new raw ID appears mid-frame. If its appearance descriptor matches with cosine ≥ 0.90, it gets the old stable ID. A person lost at an edge is treated as having left and is never relinked. The descriptor is `appearance_descriptor` from `camera_handoff.py`, reused here, with a running mean so one half-hidden frame can't dominate.
2. **Young duplicate fold-back.** During an occlusion the tracker often starts a new ID while the old one shrinks to a partial box, such as just a head. When the old ID dies mid-frame inside a box that is under 1 s old, and appearance matches, the young ID is merged back into the old one.

There is a known limit, marked in the code with `shortcut:`: exits are only the left and right edges. Doors are not modelled.

### 2.5 Stage 3: role per person (`RoleClassifier` + `CustEmpClassifier`)

**Factors, each an employee-evidence score:**

| Factor | Weight | Source | Why |
|---|---|---|---|
| `yolo` | 0.55 | `best.pt` class: `+conf` for employee, `−conf` for customer | Main signal; a confidence of about 0.82 or more is enough on its own |
| `bib_colour` | 0.30 | HSV mask over the middle torso (face, legs and background cut out) | Steadier than the model on people wearing bibs |
| `staff_zone` | 0.10 | Time in configured staff-only regions such as tills or counters | Supporting evidence only |
| `stationary` | 0.05 | Time spent still (within 18 px) | Supporting evidence only |

- **Decision:** the weighted sum is clipped to [0, 1]; `employee` if it is ≥ 0.45. With no YOLO evidence, its weight moves to bib colour.
- **Why zone and stationary weights are tiny:** together they reach only 0.15, so they can never decide a role alone. A customer who lingers in an aisle must not become "staff". This is tested in `test_staff_zone_alone_does_not_label_a_customer_as_employee`.
- **Temporal smoothing:** an exponential moving average (EMA) with α = 0.65 across frames.
- **Role hold:** a role locks once it has held for 3 s and only flips after the opposite role has held for 3 s. This ignores flicker but still corrects an ID that jumped to another person.
- **Separate role model, if given via `--roles`:** it runs once on the full frame and is matched to each person by IoU ≥ 0.4. Crops were tried first, but a neighbour's bib leaked into the wrong person's crop.
- **Final per-person role** (CLI `people.json`): whichever held role the ID kept for the most frames. The `role_segments` list exposes ID swaps.

### 2.6 Stage 4: proximity candidate (`engagement.py`)

The camera may be handheld or moving, and there is no floor calibration, so **all distances are in body heights** (the mean box height of the pair).

- **Body bands:** each box is split into overlapping bands: feet (65–100%), hips (25–70%) and head (0–30%). The pipeline uses the **lowest band visible on both people**:
  - feet are skipped if the box touches the bottom of the frame;
  - head is skipped if the box touches the top;
  - feet and hips are skipped if they are hidden behind a person nearer the camera (that person's box reaches lower).
- **Thresholds tighten as the band rises:** feet 1.0, hips 0.8, head 0.6 body heights. Feet are on the floor and carry real depth; higher parts carry less depth information.
- **Depth guard:** if the shorter box is under 0.6× the taller one, the two people are at different depths, however close they look in the image.
- **Pass-by filter:** the customer's offset from the employee is recorded in body heights, so camera motion cancels out. If that offset drifts more than 0.5 body heights before `min_interaction_seconds` (2 s), the clock restarts. Walking pace is about 0.8 heights/s, so a passer-by never survives.
- **Lifecycle:** an event ends after 1.5 s unseen (`max_missing_seconds`). Only events of 2 s or more are emitted.

### 2.7 Stage 5: pose judge (`pose.py`, the second model)

Proximity only *nominates* a pair; two people standing back-to-back near a shelf are close but not interacting.

- **Model:** `yolov8n-pose.pt` at 320 px. Pair crops are about 300–500 px, so 640 would only upsample.
- **Input:** `judge_frames = 4` crops of the pair, spread over the last 2 s. They come from a rolling frame buffer in `pipeline._recent`, with a 15% margin around the union box.
- **Head direction:**
  - The base estimate is the nose minus the midpoint of the two ears (`core.head_direction`).
  - If only one ear is visible (head in profile), it uses nose minus that ear.
  - With no nose visible (back to the camera) there is no evidence either way.
- **Facing test:** the head vector must point at the *other person's head* (15% down their box, not the box centre, which sits well below eye level at conversation range) within a 60° cone. The cone is wide because 2D head direction is coarse.
- **Verdict:** `interaction` if at least one of the pair faces the other in ≥ 50% of the frames where a pose was found. Otherwise `no_interaction`. If no pose is found at all, the result is `unknown`.
- **Fail-safe:**
  - If the judge throws an error or finds no pose, the verdict is `unverified`, and `CONFIRMED = ("interaction", "unverified")`. A broken judge never loses a proximity result.
  - A rejected pair is re-judged every 4 s while still close, because people turn to talk.
- **Runs inline on purpose:** a background-thread version slowed every later detector frame about 2× through thread-pool contention. Inline, it costs about 250 ms once per candidate.
- **Device:** `--judge-device cuda:0` can move only the judge to the GPU.

### 2.8 Output (`cli.py`)

```
python -m backend.interaction.cli video.mp4 --track-every 3 --every 15 --output out.mp4 [--judge pose|off] [--device cuda:0]
```

- `--track-every N`: feed the tracker every N frames, so IDs survive crossings.
- `--every N`: score roles and interactions and write output every N frames.

| File | Contents |
|---|---|
| `out.mp4` | Boxes coloured by role, band lines, green links for confirmed pairs, "INTERACTION: ON/OFF" banner |
| `.detections.json` | Every processed frame: ID, box, confidence, role, factor evidence, `interaction_active` |
| `.people.json` | Per ID: mean factors, weighted contributions, score, final role, role segments |
| `.interactions.json` | Confirmed events: IDs, start, last seen, duration, distance in body heights, `measured_by`, verdict |
| `.rejected_interactions.json` | Candidates the judge vetoed |

### 2.9 Benchmark (`benchmark.py`, `benchmarks/report.json`)

**Detector**, on 455 held-out images (split by recording):

| | Precision | Recall | mAP50 |
|---|---|---|---|
| Overall | 0.963 | 0.953 | **0.969** |
| Employee | 0.968 | 0.990 | — |
| Customer | 0.958 | 0.916 | — |

mAP50-95 is 0.896, at 73 ms per image on CPU.

**Interactions:** events are matched one-to-one by temporal IoU ≥ 0.5.

| | Precision | Recall |
|---|---|---|
| Proximity only | 0.5 | 1.0 |
| With judge | **1.0** | **1.0** |

**These numbers come from just one labelled video with one true interaction.** The other 10 videos have no ground truth yet, so they give speed only. The precision and recall figures are not meaningful yet.

**Speed** (CPU, `every=10`, `track_every=10`):
- 1.16–1.54× realtime on 10 of 11 videos.
- One video reaches only 0.80×, because judge calls there averaged 890 ms. **The realtime target fails on that video.**
- Frame latency p50 is about 120–170 ms.

### 2.10 The second design: "Track A" contracts (built and tested, but not runnable on real video)

`pipeline.FrameProcessor`, `core.py`, `cv_contracts.py`, `calibration.py`, `frames.py`, `live.py`, `schemas.py`, `storage.py` and `identity.py` are a stricter, production-shaped design that matches `interaction.md`:

- **Typed Pydantic contracts:**
  - `TrackObservation` and `FrameResult`;
  - `Orientation` (must be a unit vector, or carry an explicit reason why it is unknown);
  - `Calibration`, which requires two or more reviewed tracks per role and is scoped to one camera.
- **Timestamps:**
  - `frames.recording_frames` decodes with PyAV and keeps the source timestamps (PTS); it rejects missing or backward timestamps rather than inventing them from FPS.
  - `live.LiveSource` accepts only RTSP, keeps a latest-frame queue, reconnects with exponential backoff and never logs the URL or credentials.
  - Frame timestamps must strictly increase. A gap larger than `max_observation_gap_seconds` resets the tracker, so people aren't linked across an outage.
- **Events:** `core.EventEngine` emits an engagement only when proximity, mutual facing (both people) and a minimum of 3 s all hold. Event IDs are deterministic UUIDv5 values.
- **Roles from a registry, not appearance** (`identity.IdentityRegistry` over SQLite in `storage.Store`):
  - Everyone starts as `unknown`.
  - `employee` comes only from manager registration.
  - `customer` comes only from a configured `CustomerEntryRule`, such as first seen in an entrance zone or crossing a boundary in a set direction.
  - Every role change is written to an audit log (`role_assignment`).
  - `calibration.RoleEstimator` refuses to let zone priors rescue weak appearance evidence.
- **What is missing:** `FrameProcessor` needs a `models` object with `create_tracker`, `track`, `poses` and `embed`. No such implementation exists in the repo; `gpu-and-vlm-notes.md` still refers to an `interaction/models.py` that is gone. Only `FakeModels` in `test_task_a.py` provides one. `EventEngine` and `RoleEstimator` are also used only by tests.
- **The two designs contradict each other on roles:**
  - The running pipeline (2.3–2.7) decides roles from appearance (model plus bib colour).
  - The Track A design and `interaction.md` say appearance must *never* decide a role.

  **The FYP report should say which one is authoritative.**

### 2.11 Supporting docs and config

- `ANNOTATION_GUIDE.md`: CVAT labelling rules. Split by recording day, two annotators plus an adjudicator, and held-out data never used for tuning.
- `evaluation_spec.example.json`: target acceptance limits, for example detection precision 0.9, IDF1 0.75 and event precision 0.9 / recall 0.7.
- `identity_config.example.json`: example customer-entry rules.
- `requirements-cv.txt`: pins `ultralytics==8.4.135` and `openvino==2026.4.1`, plus PyAV, SciPy and lap.

### 2.12 Tests (44 in the interaction module)

| File | What it covers |
|---|---|
| `test_engagement.py` | Minimum duration, out of range, feet-first, cut-off feet falling back to hips, hidden body falling back to head, depth guard, passer-by rejection, moving camera |
| `test_judge.py` | Rejected pairs are never flagged and are rechecked, confirmed from the first qualifying frame, broken judge keeps the proximity result, profile heads, walking away side by side |
| `test_tracker.py` | Relink after hiding, edge entry keeps a new ID, a different-looking person or expired memory keeps a new ID, young-duplicate merge |
| `test_role_classifier.py`, `test_cust_emp_classifier.py` | Bib is primary evidence, zone alone can't decide, the 3 s hold, IoU matching against the full-frame model, weight redistribution |
| `test_identity.py`, `test_task_a.py`, `test_benchmark.py` | Registry rules, Track A contracts, timestamp decoding, RTSP-only sources, temporal-IoU matching |

---

## 3. Camera handoff and global identity

- **`handoff_core.py`:** pure rules for two cameras with no OpenCV, so they can be tested on CPU.
  - An exit from cam1 past x = 0.85 is matched to an entry on cam2 past x = 0.15, within 1–45 s.
  - The match score combines appearance cosine with timing compatibility: ≥ 0.78 is confirmed, ≥ 0.52 is uncertain, and matching is one-to-one.
- **`camera_handoff.py`:**
  - Tracks both videos with `vision_inference.track_frame` (YOLOv8n plus ByteTrack).
  - Builds the colour `appearance_descriptor` that the interaction tracker reuses.
  - `attach_global_identities` binds tracks to global people through `IdentityRegistry`. Only *confirmed* matches merge identities, and customer-entry rules run on boundary crossings.
- **`camera_service.py`:** FastAPI app mounted at `/camera`, protected by a shared-secret header.
  - `POST /handoff` starts an async job; `GET /jobs/{id}` polls it.
  - `GET /people` lists global people.
  - `PUT /people/{id}/role` lets a manager register an employee or reset someone to unknown. Setting `customer` is deliberately not accepted.

## 4. Store operations API (`app.py`, `store_core.py`)

- **Auth:** PBKDF2-hashed passwords, invitation-based signup and manager/employee roles via `actor` dependencies. The Next.js server calls the backend with an internal secret header.
- **Settings:** zones, cameras, rosters, thresholds and privacy, stored in SQLite (`retailpulse.sqlite3`).
- **Alerts and tasks:**
  - `POST /orchestrator/events` records an event and creates an alert.
  - For `unattended_customer`, `unstaffed_zone` and `crowding`, it auto-dispatches a task to an employee in the target zone, unless dispatch is paused.
  - Employees move tasks through their states (`/tasks/{id}/transition`), and `/tasks/events` streams updates.
  - `/system-status` reports pipeline health.
- **Voice agent (`voice_agent.py`):**
  - An LLM on the Hugging Face router (default `Qwen2.5-7B-Instruct`) writes a short spoken announcement for an event.
  - ElevenLabs turns it into speech.
  - If no API keys are set, a template fallback script is used.
- **Device switch (`device.py`):** set `USE_GPU = True` to move every model to `cuda:0`.

## 5. Gaps to know about

1. **The interaction module is not connected to `app.py`.** No interaction results reach the store API or create alerts. The only ways to run it are the CLI and the separate service on port 8012.
2. **Two role philosophies coexist,** as described in 2.10.
3. **`FrameProcessor` has no real models implementation,** so Track A runs only in tests.
4. **Interaction accuracy rests on one labelled event.** Labelling more of the 10 benchmark videos is the next step before claiming any precision or recall.
5. **Realtime fails on one benchmark video,** because of slow judge calls.

*Not covered: the frontend, the LaTeX report and the dummy dataset CSVs. The test suite was not run while writing this, so the 44 tests are not confirmed passing.*
