from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class UserCreate(Input):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    phone: str | None = Field(default=None, max_length=30)
    role: Literal['PROTECTED_PERSON', 'CAREGIVER']
    password: str = Field(min_length=12, max_length=128)
    @field_validator('email')
    @classmethod
    def email_lower(cls, value):
        return value.lower()

class Login(Input):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

class FamilyCreate(Input):
    name: str = Field(min_length=1, max_length=100)

class MemberCreate(Input):
    user_id: str
    relationship: str = Field(min_length=1, max_length=60)
    join_code: str = Field(default='', max_length=100)

class ConsentCreate(Input):
    family_id: str
    protected_person_id: str
    scope: Literal['DIGITAL_SAFETY'] = 'DIGITAL_SAFETY'
    external_ai_allowed: bool = False

class MessageInput(Input):
    family_id: str
    sender_id: str
    content: str = Field(min_length=1, max_length=10000)
    source: Literal['SIMULATOR', 'MANUAL', 'API'] = 'MANUAL'
    request_id: str | None = Field(default=None, min_length=1, max_length=100)

class Feedback(Input):
    label: Literal['TRUE_RISK', 'FALSE_POSITIVE', 'MISSED_RISK']
