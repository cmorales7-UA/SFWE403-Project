"""Input models for the new graduate admissions workflow."""
from typing import Literal
from pydantic import BaseModel, ConfigDict


class ProcessAdmissionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tuition_classification: Literal["resident", "nonresident"]
