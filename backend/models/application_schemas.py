"""Input validation for SRS 9.4 application workflows."""
from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    program_id: int = Field(gt=0)
    campus: str = Field(min_length=1, max_length=100)
    term: str = Field(min_length=1, max_length=100)
    fields: dict[str, str] = Field(default_factory=dict)
    submitted: bool = False


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fields: dict[str, str] = Field(min_length=1)


class PreliminaryReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    review_comments: str = Field(default="", max_length=5000)
    missing_information: str = Field(default="", max_length=5000)


class ApplicantMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


class ReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference_number: int = Field(ge=1, le=3)
