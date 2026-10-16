from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal['applicant', 'administrator', 'advisor', 'reviewer', 'reference', 'it_support']

class Registration(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=256)
    security_question_1: str = Field(min_length=1)
    security_answer_1: str = Field(min_length=1)
    security_question_2: str = Field(min_length=1)
    security_answer_2: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    net_id: str = ''
    phone: str = Field(min_length=1)
    email: str = Field(min_length=3)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        if '@' not in value or '.' not in value.rsplit('@', 1)[-1]:
            raise ValueError('Enter a valid email address')
        return value

class Login(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    username: str | None = Field(default=None, min_length=1)
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=3)
    phone: str | None = Field(default=None, min_length=1)
    net_id: str | None = None
    user_type: Role | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=256)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        return Registration.valid_email(value) if value is not None else value

class ProgramCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    degree_name: str = Field(min_length=1)
    degree_level: str = Field(min_length=1)
    degree_college: str = Field(min_length=1)
    degree_description: str = Field(min_length=1)
    campus_offered: list[Literal['main', 'online', 'distance']] = Field(min_length=1)
    terms_offered: list[str] = Field(default_factory=list)
    degree_requirements: str = Field(min_length=1)
    application_deadline: date
    application_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    sponsor_question: str = ''
    ta_ra_question: str = ''
    funding_question: str = ''
    english_test_question: str = ''
    english_score_question: str = ''
    other_requirements: str = ''
    program_contact: str = Field(min_length=1)
