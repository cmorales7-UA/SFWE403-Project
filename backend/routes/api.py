"""HTTP endpoints for UA-GDAS."""

from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from backend.models.schemas import (
    Login,
    ProgramCreate,
    Registration,
    UserUpdate,
)

from backend.models.application_schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    PreliminaryReview,
    ApplicantMessage,
    ReferenceRequest,
)

from backend.models.review_schemas import (
    ReviewAssignmentCreate,
    ReviewNotificationSend,
)

from backend.service import (
    accounts,
    programs,
    applications,
    review_committee,
    reviewer_actions,
    review_monitor,
)

router = APIRouter(prefix="/api")


def current_user(request: Request):
    return accounts.session_user(request.cookies.get("gdas_session", ""))


# Account management


@router.post("/users", status_code=201)
def register(payload: Registration):
    return accounts.register(payload)


@router.post("/login")
def login(
    payload: Login,
    request: Request,
    response: Response,
):
    user, token = accounts.authenticate(payload)

    response.set_cookie(
        "gdas_session",
        token,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        max_age=28800,
    )

    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    accounts.logout(request.cookies.get("gdas_session", ""))

    response.delete_cookie("gdas_session")


@router.get("/users")
def list_users(actor=Depends(current_user)):
    return accounts.list_users(actor)


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    actor=Depends(current_user),
):
    return accounts.update_user(
        user_id,
        payload,
        actor,
    )


# Degree programs


@router.post("/programs", status_code=201)
def create_program(
    payload: ProgramCreate,
    actor=Depends(current_user),
):
    return programs.create_program(
        payload,
        actor,
    )


@router.get("/programs")
def list_programs(actor=Depends(current_user)):
    return programs.list_programs(actor)


@router.get("/programs/{program_id}")
def get_program(
    program_id: int,
    actor=Depends(current_user),
):
    return programs.get_program(
        program_id,
        actor,
    )


@router.put("/programs/{program_id}")
def update_program(
    program_id: int,
    payload: ProgramCreate,
    actor=Depends(current_user),
):
    return programs.update_program(
        program_id,
        payload,
        actor,
    )


# SRS 9.4.1: Application management


@router.post("/applications", status_code=201)
def create_application(
    payload: ApplicationCreate,
    actor=Depends(current_user),
):
    return applications.create_application(
        payload,
        actor,
    )


@router.get("/applications")
def list_applications(actor=Depends(current_user)):
    return applications.list_applications(actor)


@router.get("/applications/{application_id}")
def get_application(
    application_id: int,
    actor=Depends(current_user),
):
    return applications.get_application(
        application_id,
        actor,
    )


@router.patch("/applications/{application_id}")
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    actor=Depends(current_user),
):
    return applications.update_application(
        application_id,
        payload,
        actor,
    )


# SRS 9.4.2: Preliminary review


@router.post("/applications/{application_id}/preliminary-review")
def preliminary_review(
    application_id: int,
    payload: PreliminaryReview,
    actor=Depends(current_user),
):
    return applications.preliminary_review(
        application_id,
        payload,
        actor,
    )


@router.post("/applications/{application_id}/request-information")
def request_information(
    application_id: int,
    actor=Depends(current_user),
):
    return applications.request_information(
        application_id,
        actor,
    )


@router.post("/applications/{application_id}/recommendation-requests")
def request_recommendation(
    application_id: int,
    payload: ReferenceRequest,
    actor=Depends(current_user),
):
    return applications.request_recommendation(
        application_id,
        payload,
        actor,
    )


# SRS 9.4.3: Applicant communication


@router.post("/applications/{application_id}/messages")
def send_application_message(
    application_id: int,
    payload: ApplicantMessage,
    actor=Depends(current_user),
):
    return applications.message_applicant(
        application_id,
        payload,
        actor,
    )


# SRS 9.4.4: Review Committee assignments and notifications


@router.get("/review-committee/reviewers")
def list_committee_reviewers(actor=Depends(current_user)):
    return review_committee.list_reviewers(actor)


@router.get("/review-committee/assignments")
def list_committee_assignments(actor=Depends(current_user)):
    return review_committee.list_assignments(actor)


@router.post("/review-committee/assignments", status_code=201)
def create_review_assignments(
    payload: ReviewAssignmentCreate,
    actor=Depends(current_user),
):
    return review_committee.create_assignments(
        payload,
        actor,
    )


@router.post("/review-committee/notifications")
def send_review_notifications(
    payload: ReviewNotificationSend,
    actor=Depends(current_user),
):
    return review_committee.send_notifications(
        payload,
        actor,
    )


# SRS 9.3.1: Reviewer application access


@router.get("/reviewer/assignments")
def list_reviewer_assignments(actor=Depends(current_user)):
    return review_committee.list_assignments(actor)


@router.get("/reviewer/applications/{application_id}")
def get_reviewer_application(
    application_id: int,
    actor=Depends(current_user),
):
    return review_committee.get_reviewer_application(
        application_id,
        actor,
    )


# SRS 9.3.2: Reviewer recommendations


class ReviewerRecommendationPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    recommendation: Literal[
        "recommend",
        "deny",
        "defer",
    ]

    comments: str = Field(
        default="",
        max_length=5000,
    )


@router.get("/reviewer/reviews")
def list_reviewer_reviews(actor=Depends(current_user)):
    return reviewer_actions.list_reviews(actor)


@router.get("/reviewer/applications/{application_id}/review")
def get_reviewer_review(
    application_id: int,
    actor=Depends(current_user),
):
    return reviewer_actions.get_review(
        application_id,
        actor,
    )


@router.post("/reviewer/applications/{application_id}/recommendation")
def submit_reviewer_recommendation(
    application_id: int,
    payload: ReviewerRecommendationPayload,
    actor=Depends(current_user),
):
    return reviewer_actions.save_recommendation(
        application_id,
        payload.recommendation,
        payload.comments,
        actor,
    )


# SRS 9.3.3: Reviewer communication with Advisor


class ReviewerMessagePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    message: str = Field(
        min_length=1,
        max_length=5000,
    )


@router.post("/reviewer/applications/{application_id}/messages")
def send_reviewer_message(
    application_id: int,
    payload: ReviewerMessagePayload,
    actor=Depends(current_user),
):
    return reviewer_actions.send_message(
        application_id,
        payload.message,
        actor,
    )


# SRS 9.4.5: Graduate College decision notifications

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from backend.service import graduate_college


class GraduateCollegeDecisionPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    decision: Literal["Recommend", "Deny", "Defer"]

    rationale: str = Field(
        min_length=1,
        max_length=5000,
    )


class GraduateCollegeNotificationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    administrator_id: int = Field(gt=0)


# Retrieve applications available to the Advisor.
@router.get("/graduate-college/applications")
def list_graduate_college_applications(
    actor=Depends(current_user),
):
    return graduate_college.list_applications(actor)


# Retrieve Administrators who can receive notifications.
@router.get("/graduate-college/administrators")
def list_graduate_college_administrators(
    actor=Depends(current_user),
):
    return graduate_college.list_administrators(actor)


# Retrieve the application decision and notification history.
@router.get("/graduate-college/applications/{application_id}")
def get_graduate_college_application(
    application_id: int,
    actor=Depends(current_user),
):
    return graduate_college.get_details(
        application_id,
        actor,
    )


# Create or update the Advisor's program decision.
@router.put("/graduate-college/applications/{application_id}/decision")
def save_graduate_college_decision(
    application_id: int,
    payload: GraduateCollegeDecisionPayload,
    actor=Depends(current_user),
):
    return graduate_college.save_decision(
        application_id,
        payload.decision,
        payload.rationale,
        actor,
    )


# Email the saved decision to the selected Administrator.
@router.post("/graduate-college/applications/{application_id}/notifications")
def notify_graduate_college(
    application_id: int,
    payload: GraduateCollegeNotificationPayload,
    actor=Depends(current_user),
):
    return graduate_college.send_notification(
        application_id,
        payload.administrator_id,
        actor,
    )


@router.get("/review-monitor/assignments")
def list_review_monitor_assignments(
    actor=Depends(current_user),
):
    return review_monitor.list_status(actor)


@router.post("/review-monitor/assignments/{assignment_id}/reminders")
def send_review_monitor_reminder(
    assignment_id: int,
    actor=Depends(current_user),
):
    return review_monitor.send_reminder(
        assignment_id,
        actor,
    )
