from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import bearer, check_login_rate, dummy_hash, get_current_user, hash_password, issue_token, require_roles, revoke_token, verify_password
from app.database import get_db
from app.models import Book, Role, User
from app.schemas import BookIn, BookOut, BorrowIn, LoanOut, LoginIn, RegisterIn, StaffIn, UserOut
from app.services import BookService, LoanService, commit_or_conflict

router = APIRouter(prefix="/api")


@router.post("/auth/register", status_code=201)
def register(data: RegisterIn, db: Annotated[Session, Depends(get_db)]) -> dict:
    user = User(name=data.name.strip(), email=str(data.email).lower(), password_hash=hash_password(data.password), role=Role.MEMBER)
    db.add(user); commit_or_conflict(db, "Email already exists"); db.refresh(user)
    return {"data": UserOut.model_validate(user)}


@router.post("/auth/login")
def login(data: LoginIn, request: Request, db: Annotated[Session, Depends(get_db)]) -> dict:
    check_login_rate(request)
    user = db.scalar(select(User).where(func.lower(User.email) == str(data.email).lower()))
    if user is None:
        verify_password(data.password, dummy_hash)
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    return {"data": {"access_token": issue_token(db, user), "token_type": "Bearer", "user": UserOut.model_validate(user)}}


@router.post("/auth/logout", status_code=204)
def logout(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)], _user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> None:
    revoke_token(db, credentials.credentials)


@router.post("/staff", status_code=201)
def create_staff(data: StaffIn, _admin: Annotated[User, Depends(require_roles(Role.ADMIN))], db: Annotated[Session, Depends(get_db)]) -> dict:
    if data.role not in (Role.ADMIN, Role.LIBRARIAN):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Staff role must be ADMIN or LIBRARIAN")
    user = User(name=data.name.strip(), email=str(data.email).lower(), password_hash=hash_password(data.password), role=data.role)
    db.add(user); commit_or_conflict(db, "Email already exists"); db.refresh(user)
    return {"data": UserOut.model_validate(user)}


@router.get("/books")
def list_books(db: Annotated[Session, Depends(get_db)], search: str = Query("", max_length=200), available: bool | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)) -> dict:
    return BookService(db).list(search, available, page, limit)


@router.post("/books", status_code=201)
def create_book(data: BookIn, actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.LIBRARIAN))], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": BookOut.model_validate(BookService(db).create(data, actor))}


@router.get("/books/{book_id}")
def get_book(book_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    item = db.get(Book, book_id)
    if item is None or not item.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
    return {"data": BookOut.model_validate(item)}


@router.put("/books/{book_id}")
def update_book(book_id: int, data: BookIn, actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.LIBRARIAN))], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": BookOut.model_validate(BookService(db).update(book_id, data, actor))}


@router.post("/loans", status_code=201)
def borrow(data: BorrowIn, actor: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": LoanOut.model_validate(LoanService(db).borrow(data.book_id, data.loan_days, actor))}


@router.get("/loans")
def loans(actor: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], active: bool | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)) -> dict:
    return LoanService(db).list(actor, active, page, limit)


@router.patch("/loans/{loan_id}/return")
def return_book(loan_id: int, actor: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": LoanOut.model_validate(LoanService(db).return_book(loan_id, actor))}


@router.get("/reports/overdue")
def overdue(_staff: Annotated[User, Depends(require_roles(Role.ADMIN, Role.LIBRARIAN))], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": [LoanOut.model_validate(item) for item in LoanService(db).overdue()]}


@router.get("/dashboard")
def dashboard(actor: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict:
    if actor.role == Role.MEMBER:
        return {"data": {"active_loans": LoanService(db).list(actor, True, 1, 100)["meta"]["total"]}}
    return {"data": {"books": db.scalar(select(func.count()).select_from(Book)) or 0, "available_copies": db.scalar(select(func.coalesce(func.sum(Book.available_copies), 0))) or 0, "overdue_loans": len(LoanService(db).overdue())}}

