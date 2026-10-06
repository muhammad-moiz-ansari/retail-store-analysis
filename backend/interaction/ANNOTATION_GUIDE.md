# Interaction Dataset Annotation Guide

Annotate source recordings only. Do not annotate tracked or rendered output
videos. Keep the recording ID, camera ID, recording day, and UTC anchor with
every export.

## Labels

- Draw a `person` box for every visible person, including partial and
  occluded people when a human can identify the person as present.
- Keep the same track label through an occlusion. Start a new label after a
  true exit and re-entry; never reconnect labels across recordings or days.
- Ground-truth `employee`, `customer`, or `unknown` labels are for evaluation
  only and should be based on reviewed operational context, not clothing
  color. Production roles come from registration/entry rules; use `unknown`
  whenever the ground truth cannot be established.
- Mark facing as an image-plane unit vector using +x right and +y down. Mark
  orientation `unobservable` when the head is occluded, too small, or the
  direction cannot be decided. Do not infer compass direction.
- Mark an engagement interval only when the employee/customer pair is
  visibly close and mutually facing. Record start and end source timestamps;
  do not round them to processing time.

## Quality control

Two annotators review the development and held-out samples. A third reviewer
adjudicates disagreements about track continuity, role, facing, or event
boundaries. Store the annotation version and adjudication status in the
dataset manifest.

## Splits

Split by recording day and leakage group before extracting crops. Keep
training, calibration, development, and held-out recordings disjoint. Held-out
labels must not be used for prototypes, threshold selection, or model choice.
