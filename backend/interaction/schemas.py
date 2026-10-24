from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
Unit = Annotated[float, Field(ge=0, le=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Zone(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    polygon: list[tuple[Unit, Unit]] = Field(min_length=3, max_length=32)
    employee_prior: float = Field(default=0, ge=-1, le=1)

    @field_validator("polygon")
    @classmethod
    def nondegenerate(cls, points):
        area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
        if abs(area) < 1e-6:
            raise ValueError("Zone polygon must have nonzero area")
        return points


class CameraConfig(StrictModel):
    camera_id: Identifier
    zones: list[Zone] = Field(default_factory=list, max_length=30)
    distance_threshold: float = Field(default=0.15, gt=0, le=1.5)
    facing_angle_degrees: float = Field(default=45, gt=0, le=90)
    min_duration_seconds: float = Field(default=3, gt=0, le=300)
    max_observation_gap_seconds: float = Field(default=1, gt=0, le=10)
    orientation_confidence: Unit = 0.5
    role_similarity: Unit = 0.65
    role_margin: float = Field(default=0.08, gt=0, le=1)
    prior_weight: float = Field(default=0.05, ge=0, le=0.2)
    dwell_seconds: float = Field(default=300, gt=0, le=86400)
    customer_entry_rules: list["CustomerEntryRule"] = Field(default_factory=list, max_length=20)

    @field_validator("zones")
    @classmethod
    def unique_zones(cls, zones):
        if len({zone.name for zone in zones}) != len(zones):
            raise ValueError("Zone names must be unique")
        return zones


class CustomerEntryRule(StrictModel):
    """An explicit context that may promote UNKNOWN to CUSTOMER."""

    name: Identifier
    camera_id: Identifier
    event: Literal["first_seen", "boundary_crossing"]
    zone: str | None = Field(default=None, min_length=1, max_length=80)
    boundary: Literal["left", "right"] | None = None
    direction: Literal["left", "right"] | None = None

    @model_validator(mode="after")
    def has_context(self):
        if self.zone is None and self.boundary is None:
            raise ValueError("Customer entry rule requires a zone or boundary")
        if self.event == "first_seen" and self.zone is None:
            raise ValueError("first_seen customer rule requires a zone")
        if self.event == "boundary_crossing" and (self.boundary is None or self.direction is None):
            raise ValueError("boundary_crossing customer rule requires boundary and direction")
        return self

    def matches(self, context: dict) -> bool:
        return (
            context.get("camera_id") == self.camera_id
            and context.get("event") == self.event
            and (self.zone is None or context.get("zone") == self.zone)
            and (self.boundary is None or context.get("boundary") == self.boundary)
            and (self.direction is None or context.get("direction") == self.direction)
        )


class RoleAssignmentRequest(StrictModel):
    role: Literal["employee", "unknown"]
    assigned_by: str = Field(min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=500)
