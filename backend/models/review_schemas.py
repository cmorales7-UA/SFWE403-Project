from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
)


# Reviewer Assignment
class ReviewAssignmentCreate(BaseModel):
    """
    Assign one or more applications to one or more
    reviewers with a specified review deadline.
    """

    model_config = ConfigDict(extra="forbid")

    application_ids: list[PositiveInt] = Field(
        min_length=1
    )

    reviewer_ids: list[PositiveInt] = Field(
        min_length=1
    )

    due_date: date

    @field_validator("application_ids", "reviewer_ids")
    @classmethod
    def validate_unique_ids(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Duplicate IDs are not allowed")

        return values

# Reviewer Email Notifications
class ReviewNotificationSend(BaseModel):
    """
    Send initial review notifications for selected
    assignments.

    The backend groups assignments by reviewer,
    allowing one email per reviewer.
    """

    model_config = ConfigDict(extra="forbid")

    assignment_ids: list[PositiveInt] = Field(
        min_length=1
    )

    @field_validator("assignment_ids")
    @classmethod
    def validate_unique_assignments(cls, values):
        if len(values) != len(set(values)):
            raise ValueError(
                "Duplicate assignment IDs are not allowed"
            )

        return values
