"""Input validation for SRS 9.4 application workflows."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class GraduateCollegeReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    notes: str | None = Field(default=None, max_length=5000)
    review_comments: str | None = Field(default=None, max_length=5000)
    decision: Literal["Recommend", "Deny", "Defer"] | None = None
    rationale: str | None = Field(default=None, max_length=5000)
    decision_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_review(self):
        if (self.decision is None) != (self.rationale is None):
            raise ValueError("A recommendation and rationale must be saved together")
        if self.decision is not None and not self.rationale:
            raise ValueError("Enter a rationale for the recommendation")
        if all(value is None for value in (
            self.notes, self.review_comments, self.decision
        )):
            raise ValueError("No review changes were submitted")
        return self


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
