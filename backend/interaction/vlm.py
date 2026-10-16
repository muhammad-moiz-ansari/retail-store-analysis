"""Small, optional VLM adapters for semantic role and interaction checks.

The CV pipeline owns localisation and tracking.  A VLM only receives a person
crop or a short pair window and returns a constrained semantic result.  This
keeps the core pipeline usable on machines where Transformers/a VLM are not
installed and makes the model replaceable for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class VLMResult:
    label: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)


class VLMClassifier(Protocol):
    def classify_role(self, crop_bgr: Any) -> VLMResult: ...

    def classify_interaction(self, frames_bgr: list[Any]) -> VLMResult: ...


class NullVLM:
    """Explicit disabled adapter; useful for CPU-only deployments and tests."""

    def classify_role(self, crop_bgr: Any) -> VLMResult:
        return VLMResult("unknown", 0.0, {"reason": "vlm_disabled"})

    def classify_interaction(self, frames_bgr: list[Any]) -> VLMResult:
        return VLMResult("unknown", 0.0, {"reason": "vlm_disabled"})


class SmolVLMClassifier:
    """Lazy Transformers adapter for HuggingFaceTB/SmolVLM2 models.

    Loading is delayed until the first request so the rest of the application
    (including tests and detector-only deployments) does not import a large
    model.  The prompt deliberately requires one of the small, auditable label
    sets; parsing is conservative and falls back to ``unknown``.
    """

    def __init__(self, model_id: str = "HuggingFaceTB/SmolVLM2-500M-Video-Instruct",
                 device: str = "cpu", max_new_tokens: int = 8):
        self.model_id, self.device = model_id, device
        self.max_new_tokens = max_new_tokens
        self._processor = None
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        from transformers import AutoProcessor
        # Transformers 5 renamed this auto class; keep compatibility with
        # older releases used by the main application environment.
        try:
            from transformers import AutoModelForImageTextToText as ModelClass
        except ImportError:
            from transformers import AutoModelForVision2Seq as ModelClass
        self._processor = AutoProcessor.from_pretrained(self.model_id)
        self._model = ModelClass.from_pretrained(self.model_id).to(self.device).eval()

    @staticmethod
    def _label(text: str, labels: tuple[str, ...]) -> str:
        lowered = text.lower()
        for label in labels:
            if label in lowered:
                return label
        return "unknown"

    def _ask(self, images: list[Any], prompt: str) -> str:
        from PIL import Image
        self._load()
        converted = [Image.fromarray(image[:, :, ::-1].copy()) for image in images]
        conversation = [{"role": "user", "content": [
            *({"type": "image"} for _ in converted), {"type": "text", "text": prompt}
        ]}]
        text = self._processor.apply_chat_template(conversation, add_generation_prompt=True)
        inputs = self._processor(text=text, images=converted, return_tensors="pt").to(self.device)
        output = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens)
        return self._processor.batch_decode(output, skip_special_tokens=True)[0]

    def classify_role(self, crop_bgr: Any) -> VLMResult:
        raw = self._ask([crop_bgr],
            "Classify the visible person as exactly employee, customer, or unknown. "
            "Employees wear the configured bright orange reflective vest. If unclear, say unknown. "
            "Return only: employee, customer, or unknown.")
        label = self._label(raw, ("employee", "customer"))
        if label == "unknown":
            return VLMResult(label, 0.0, {"raw": raw})
        return VLMResult(label, 0.75, {"raw": raw, "model": self.model_id})

    def classify_interaction(self, frames_bgr: list[Any]) -> VLMResult:
        raw = self._ask(frames_bgr,
            "Across this short CCTV window, decide whether an employee and customer are visibly "
            "engaged with each other. Consider sustained proximity, mutual facing, and gestures. "
            "Return only interaction or no_interaction.")
        label = self._label(raw, ("no_interaction", "interaction"))
        return VLMResult(label, 0.75 if label != "unknown" else 0.0,
                         {"raw": raw, "model": self.model_id})
