"""Clip Review (Ruhab): human checks of CV events against their recorded footage.

A reviewer opens the short clip behind an interaction or unattended episode and records
confirmed / rejected / unsure. The results give a measured precision per event kind and,
with a second reviewer, an inter-annotator agreement (Cohen's kappa) for CV-REVIEW.

Inputs:
- `RecordingSource` is trusted server configuration mapping a CV run/camera to a recorded
  video and its UTC start instant. The event store does not record this today, so Saqib's
  ingestion config must supply it. `video_ref` is an opaque ID resolved by the server,
  never a client-supplied file path.
- `ClipCandidate`s come from scoped results (`from_unattended`) or from interaction event
  rows that a trusted reader supplies (`from_interaction_rows`).

Blind review hides the CV verdict and helped flag, so rechecks such as IMG_8838 p2 and
IMG_8830 are not anchored on the detector's answer. Nothing here plays video or writes a
database; `ReviewLedger` is an in-memory reference implementation of the storage protocol.
"""
from datetime import datetime, timedelta
from typing import Annotated, Literal, Protocol

from pydantic import Field, field_validator, model_validator

from ..contracts import Contract, Identifier, TimeWindow

Kind = Literal['interaction', 'unattended']
# Opaque server-side key: no path separators or parent references can reach a file lookup.
VideoRef = Annotated[str, Field(strict=True, min_length=1, max_length=200, pattern=r'^[A-Za-z0-9_:-][A-Za-z0-9._:-]*$')]
Decision = Literal['confirmed', 'rejected', 'unsure']


class RecordingSource(Contract):
    run_id: Identifier
    camera_id: Identifier
    store_id: Identifier
    video_ref: VideoRef
    started_at: datetime
    duration_s: float = Field(gt=0)

    @field_validator('started_at', mode='before')
    @classmethod
    def aware(cls, value):
        return TimeWindow.aware_iso_input(value)


class ClipCandidate(Contract):
    event_id: Identifier
    kind: Kind
    store_id: Identifier
    run_id: Identifier
    camera_id: Identifier
    zone_id: Identifier
    window: TimeWindow
    cv_verdict: Literal['interaction', 'unverified', 'unhelped', 'helped']
    synthetic: bool


class ClipSegment(Contract):
    video_ref: VideoRef
    offset_start_s: float = Field(ge=0)
    offset_end_s: float = Field(gt=0)

    @model_validator(mode='after')
    def ordered(self):
        if self.offset_end_s <= self.offset_start_s:
            raise ValueError('Clip must have positive length')
        return self


class ReviewItem(Contract):
    event_id: Identifier
    kind: Kind
    zone_id: Identifier
    window: TimeWindow
    clip: ClipSegment | None
    unavailable_reason: Literal['no_recording', 'outside_recording'] | None = None
    cv_verdict: str | None  # None in blind mode
    synthetic: bool


class ReviewVerdict(Contract):
    event_id: Identifier
    reviewer_id: Identifier
    decision: Decision
    reviewed_at: datetime
    note: str | None = Field(default=None, max_length=1000)

    @field_validator('reviewed_at', mode='before')
    @classmethod
    def aware(cls, value):
        return TimeWindow.aware_iso_input(value)


def from_unattended(result):
    """Unattended episodes from a scoped `UnattendedResult`; helped=True episodes are review-able too."""
    return tuple(ClipCandidate(event_id=e.event_id, kind='unattended', store_id=result.scope.store_id, run_id=e.run_id,
                               camera_id=e.camera_id, zone_id=e.zone_id, window=e.window,
                               cv_verdict='helped' if e.helped else 'unhelped', synthetic=result.synthetic)
                 for e in result.episodes)


def from_interaction_rows(rows, *, synthetic: bool):
    """Rows shaped like the `interactions` table (event_id, run/store/camera/zone, ts_start/ts_end, verdict)."""
    out = []
    for row in rows:
        if row['verdict'] not in ('interaction', 'unverified'):
            continue
        start, end = (TimeWindow.aware_iso_input(row[key]) for key in ('ts_start', 'ts_end'))
        # Instant events (ts_end == ts_start) still get a one-second reviewable span.
        out.append(ClipCandidate(event_id=row['event_id'], kind='interaction', store_id=row['store_id'], run_id=row['run_id'],
                                 camera_id=row['camera_id'], zone_id=row['zone_id'],
                                 window=TimeWindow(start=start, end=max(end, start + timedelta(seconds=1))),
                                 cv_verdict=row['verdict'], synthetic=synthetic))
    return tuple(out)


def review_items(candidates, sources, *, pad_s=3.0, blind=False):
    """Map each candidate to a padded clip inside its recording, or an explicit unavailable reason."""
    index = {(s.store_id, s.run_id, s.camera_id): s for s in sources}
    items = []
    for c in candidates:
        source = index.get((c.store_id, c.run_id, c.camera_id))
        clip, reason = None, None
        if source is None:
            reason = 'no_recording'
        else:
            start = (c.window.start - source.started_at).total_seconds()
            end = (c.window.end - source.started_at).total_seconds()
            if end <= 0 or start >= source.duration_s:
                reason = 'outside_recording'
            else:
                clip = ClipSegment(video_ref=source.video_ref, offset_start_s=max(0.0, start - pad_s),
                                   offset_end_s=min(source.duration_s, end + pad_s))
        items.append(ReviewItem(event_id=c.event_id, kind=c.kind, zone_id=c.zone_id, window=c.window, clip=clip,
                                unavailable_reason=reason, cv_verdict=None if blind else c.cv_verdict, synthetic=c.synthetic))
    return tuple(items)


class ReviewStore(Protocol):
    def record(self, verdict: ReviewVerdict) -> None: ...
    def verdicts(self) -> tuple[ReviewVerdict, ...]: ...


class ReviewLedger:
    """In-memory reference store: the latest verdict per (event, reviewer) wins."""

    def __init__(self, known_event_ids=()):
        self._known = frozenset(known_event_ids)
        self._latest = {}

    def record(self, verdict: ReviewVerdict) -> None:
        verdict = ReviewVerdict.model_validate(verdict)
        if self._known and verdict.event_id not in self._known:
            raise ValueError('Verdict refers to an event that is not in this review set')
        key = (verdict.event_id, verdict.reviewer_id)
        current = self._latest.get(key)
        if current is None or verdict.reviewed_at >= current.reviewed_at:
            self._latest[key] = verdict

    def verdicts(self):
        return tuple(self._latest.values())


class KindSummary(Contract):
    kind: Kind
    cv_verdict: str
    events: int
    confirmed: int
    rejected: int
    unsure: int
    pending: int
    precision: float | None  # confirmed / (confirmed + rejected); None without decisive reviews


class Agreement(Contract):
    reviewers: tuple[Identifier, Identifier]
    shared_events: int
    percent_agreement: float | None
    cohen_kappa: float | None


class ReviewSummary(Contract):
    synthetic: bool | None  # None for an empty review set
    by_verdict: tuple[KindSummary, ...]
    agreement: Agreement | None = None


def _majority(decisions):
    """Per event: confirmed/rejected only when every decisive reviewer agrees; otherwise unsure."""
    decisive = {d for d in decisions if d != 'unsure'}
    return decisive.pop() if len(decisive) == 1 else 'unsure'


def agreement(verdicts, first, second):
    a = {v.event_id: v.decision for v in verdicts if v.reviewer_id == first}
    b = {v.event_id: v.decision for v in verdicts if v.reviewer_id == second}
    shared = sorted(set(a) & set(b))
    if not shared:
        return Agreement(reviewers=(first, second), shared_events=0, percent_agreement=None, cohen_kappa=None)
    observed = sum(a[e] == b[e] for e in shared) / len(shared)
    labels = ('confirmed', 'rejected', 'unsure')
    expected = sum((sum(a[e] == l for e in shared) / len(shared)) * (sum(b[e] == l for e in shared) / len(shared)) for l in labels)
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    return Agreement(reviewers=(first, second), shared_events=len(shared), percent_agreement=observed, cohen_kappa=kappa)


def summarise(candidates, store: ReviewStore, *, second_reviewer_pair=None):
    candidates = tuple(candidates)
    if len({c.synthetic for c in candidates}) > 1:
        raise ValueError('Do not mix synthetic and real events in one review summary')
    verdicts = store.verdicts()
    per_event = {}
    for v in verdicts:
        per_event.setdefault(v.event_id, []).append(v.decision)
    groups = {}
    for c in candidates:
        groups.setdefault((c.kind, c.cv_verdict), []).append(c.event_id)
    rows = []
    for (kind, cv_verdict), ids in sorted(groups.items()):
        outcome = [_majority(per_event[i]) if i in per_event else 'pending' for i in ids]
        confirmed, rejected = outcome.count('confirmed'), outcome.count('rejected')
        rows.append(KindSummary(kind=kind, cv_verdict=cv_verdict, events=len(ids), confirmed=confirmed, rejected=rejected,
                                unsure=outcome.count('unsure'), pending=outcome.count('pending'),
                                precision=confirmed / (confirmed + rejected) if confirmed + rejected else None))
    pair = agreement(verdicts, *second_reviewer_pair) if second_reviewer_pair else None
    return ReviewSummary(synthetic=candidates[0].synthetic if candidates else None, by_verdict=tuple(rows), agreement=pair)
