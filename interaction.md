# Interaction Module — Employee-Customer Engagement Tracking

## 1. Overview

The Interaction Module is one of the three core pillars of the retail analytics FYP. It uses overhead CCTV footage to detect and track people, resolves anonymous global identities, and then determines whether a registered employee and a context-resolved customer are engaged in an interaction — including whether they are oriented toward (facing) each other.

**Pipeline summary:** each synchronized CCTV feed covers one configured zone. YOLOv8n detects people, ByteTrack supplies camera-local tracks, appearance embeddings support Re-ID, and an optional small VLM classifies person crops and short interaction windows. The persistent Global Person registry remains authoritative when a manager has registered a role; low-confidence VLM results stay `unknown`.

## 2. Objectives

- Detect all people present in the camera's field of view in real time.
- Maintain consistent identities for each detected person across frames (tracking).
- Give each tracked person an anonymous Global Person ID and an `employee`, `customer`, or `unknown` role.
- Estimate whether a given employee-customer pair is engaged in an interaction, using proximity, orientation, and duration as signals.
- Emit structured interaction events that downstream AI agents (Insight Narration, Anomaly Investigation, Recommendation) can consume.

## 3. Pipeline Architecture

```
CCTV Frame
    │
    ▼
[1] YOLOv8n — Person Detection
    │  (bounding boxes per person, per frame)
    ▼
[2] ByteTrack — Multi-Object Tracking
    │  (assigns persistent track ID per person)
    ▼
[3] Re-ID / Global Person Resolution
    │  (appearance is identity evidence, never role evidence)
    ▼
[4] Short Track Windows
    │  (sampled person crops, cached per track)
    ▼
[5] VLM Role Classification
    │  (employee/customer/unknown; confidence threshold)
    ▼
[6] Role Registry + Orientation
    │  (facing direction per tracked person)
    ▼
[7] VLM Interaction Check
    │  (short employee/customer window; interaction/no_interaction)
    ▼
[8] Engagement Event Logic
    │  (distance + orientation + VLM + duration thresholds)
    ▼
Structured Interaction Events → Agent Layer / Dashboard
```

### 3.1 Stage 1 — Person Detection (YOLOv8n)

- **Model:** YOLOv8n (nano variant, chosen for speed/compute given Kaggle T4×2 hardware budget)
- **Input resolution:** 960×960 (consistent with the rest of the CV pipeline)
- **Output:** per-frame bounding boxes for the "person" class
- **Training data:** frames extracted from supermarket CCTV recordings, labeled in CVAT

### 3.2 Stage 2 — Multi-Object Tracking (ByteTrack)

- **Purpose:** convert per-frame detections into consistent per-person tracks across time
- **Why ByteTrack:** handles low-confidence detections (partial occlusion, overhead angle) better than simple IOU trackers, and is lightweight enough to run alongside detection in real time
- **Output:** a track ID per person, persisted across frames until the person leaves the camera's view or is occluded beyond recovery

### 3.3 Stage 3 — Re-ID / Global Person Resolution

- **Purpose:** reconcile camera-local tracks to an anonymous Global Person ID.
- **Evidence:** sampled appearance embeddings, direction, and timing may support a match. Clothing color is not a role rule.
- **Conservative merge:** only confirmed Re-ID/handoff matches share an ID. Uncertain or unmatched tracks remain separate people.
- **Privacy:** the Global Person ID is an opaque technical identifier, not a name, face identity, or employee account.

### 3.4 Stage 4 — Authoritative Role Registry

- Every new or unresolved Global Person starts as `unknown`.
- During employee initialization, a manager or configured registration mechanism assigns an observed Global Person ID the `employee` role.
- The role is stored against the Global Person ID, so confirmed Re-ID across cameras preserves it.
- A non-registered person becomes `customer` only when a configured entry/context rule matches (for example, crossing the public entrance boundary in the configured direction).
- A customer-entry rule never overwrites an existing employee role.
- Appearance, uniform color, dwell time, and zone priors do not independently assign employee/customer roles. They can be retained as review or identity-association evidence.

## 4. Orientation / "Are They Looking at Each Other" Estimation

True gaze estimation (pupil-level) is not feasible from an overhead CCTV angle. Instead, the module estimates **body/head orientation** as a proxy for attention:

- Derive a facing-direction vector per tracked person (from pose keypoints or head-bounding-box orientation, depending on what the compute budget allows on top of the three core models above).
- Two people are considered **oriented toward each other** if their facing vectors converge within an angular threshold and their positions fall within a proximity threshold.
- This is explicitly a proxy ("oriented toward"), not literal gaze ("looking at") — this distinction should be stated in the FYP report's limitations section.

## 5. Engagement Event Definition

An **engagement event** between an employee track and a customer track is flagged when, for a sustained duration:

| Condition | Description |
|---|---|
| Proximity | Distance between employee and customer tracks is below a defined threshold |
| Orientation | Both tracks' facing vectors converge toward each other (within angular threshold) |
| Duration | Condition holds continuously for at least a minimum duration (e.g., a few seconds) to filter out incidental passes |

When all three hold, the module emits an interaction event with:

- Employee track ID (or zone/shift assignment — see §7)
- Customer track ID
- Start/end timestamp
- Duration
- Zone/camera location

## 6. Output Schema (draft)

```json
{
  "event_type": "engagement",
  "employee_zone": "Zone A",
  "employee_shift": "9am-1pm",
  "employee_track_id": "person-a81f...",
  "customer_track_id": "person-41be...",
  "start_time": "2026-09-14T11:32:04Z",
  "end_time": "2026-09-14T11:32:51Z",
  "duration_seconds": 47,
  "camera_id": "cam_2_instore"
}
```

## 7. Privacy-Preserving Identity Handling

Employees remain anonymous to the CV layer. The Global Person ID preserves technical continuity and role, while reports can continue to aggregate by **zone and shift assignment** rather than exposing a named identity. Registration stores role provenance and manager/config source, not a biometric identity.

## 8. Data & Training Notes

- **Data source:** CCTV recordings from the partner supermarket, converted to frames for detection training; video-native labeling in CVAT for tracking/detection annotation
- **Labeling tool:** CVAT (self-hosted, free), using built-in detector + tracker features directly on video files
- **Compute:** Kaggle T4×2 GPUs
- **Resolution:** 960×960 across the pipeline for consistency

## 9. Limitations

- Orientation-based "facing each other" is a proxy for attention, not verified eye contact or gaze.
- Single-store dataset for now — model generalization to other store layouts/camera placements is untested.
- Global Re-ID can fail under occlusion or major appearance changes; failed or uncertain matches must not inherit a role.
- Entry rules require correct camera, boundary/zone, and direction configuration. Without a matching rule, a non-registered person remains `unknown`.
- Overhead camera angle limits pose/orientation estimation accuracy compared to eye-level cameras.

## 10. Integration with Agent Layer

Interaction events feed into:
- **Insight Narration agent** — converts events into plain-language summaries (e.g., "Employee in Zone A engaged with 12 customers this shift, avg. 38s per interaction")
- **Anomaly Investigation agent** — flags unusual patterns (e.g., zones with unusually low engagement duration)
- **Recommendation/Planning agent** — uses zone/shift-level engagement patterns to inform staffing suggestions
