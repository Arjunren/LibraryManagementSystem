from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    role: Role
    is_active: bool


class StaffIn(RegisterIn):
    role: Role


class BookIn(BaseModel):
    isbn: str = Field(min_length=10, max_length=20, pattern=r"^[0-9Xx-]+$")
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    total_copies: int = Field(ge=0, le=100000)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    isbn: str
    title: str
    author: str
    description: str | None
    total_copies: int
    available_copies: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BorrowIn(BaseModel):
    book_id: int = Field(ge=1)
    loan_days: int = Field(default=14, ge=1, le=60)


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    member_id: int
    book_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None

