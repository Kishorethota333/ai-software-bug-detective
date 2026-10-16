from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl
from typing import Optional
from datetime import datetime

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; email: str; role: str
class TokenOut(BaseModel):
    access_token: str; token_type: str = "bearer"; user: UserOut
class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=10000)
    technology: str = Field(default="", max_length=255)
    repository_url: str = Field(default="", max_length=500)
class ProjectOut(ProjectIn):
    model_config = ConfigDict(from_attributes=True)
    id: int; owner_id: int; created_at: datetime
class BugIn(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    description: str = Field(default="", max_length=20000)
    error_message: str = Field(default="", max_length=20000)
    reproduction_steps: str = Field(default="", max_length=10000)
    expected_result: str = Field(default="", max_length=10000)
    actual_result: str = Field(default="", max_length=10000)
    module: str = Field(default="General", max_length=120)
    environment: str = Field(default="Development", max_length=120)
    severity: str = "MEDIUM"
    status: str = "OPEN"
    project_id: int
class BugOut(BugIn):
    model_config = ConfigDict(from_attributes=True)
    id: int; reporter_id: int; created_at: datetime; updated_at: datetime
class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; bug_id: int; root_cause: str; confidence: float; severity: str; affected_component: str; possible_causes: str; suggested_fix: str; recommended_actions: str; provider: str; created_at: datetime
class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; bug_id: int; scenario: str; input_data: str; expected_result: str; priority: str; test_type: str; executed: bool
class TestCaseUpdate(BaseModel):
    executed: bool
