from datetime import datetime, timedelta, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ActivityLog, Book, Loan, Role, User
from app.repositories import BookRepository
from app.schemas import BookIn, BookOut, LoanOut


def commit_or_conflict(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, message) from None


class BookService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: BookIn, actor: User) -> Book:
        item = Book(**data.model_dump(), available_copies=data.total_copies, created_by=actor.id, updated_by=actor.id)
        item.isbn = item.isbn.replace("-", "").upper()
        self.db.add(item)
        commit_or_conflict(self.db, "ISBN already exists")
        self.db.refresh(item)
        return item

    def update(self, book_id: int, data: BookIn, actor: User) -> Book:
        item = self.db.scalar(select(Book).where(Book.id == book_id).with_for_update())
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
        checked_out = item.total_copies - item.available_copies
        if data.total_copies < checked_out:
            raise HTTPException(status.HTTP_409_CONFLICT, "Total copies cannot be lower than checked-out copies")
        item.isbn, item.title, item.author = data.isbn.replace("-", "").upper(), data.title.strip(), data.author.strip()
        item.description, item.available_copies, item.total_copies = data.description, data.total_copies - checked_out, data.total_copies
        item.updated_by = actor.id
        commit_or_conflict(self.db, "ISBN already exists")
        self.db.refresh(item)
        return item

    def list(self, search: str, available: bool | None, page: int, limit: int) -> dict:
        items, total = BookRepository(self.db).list(search.strip(), available, page, limit)
        return {"data": [BookOut.model_validate(item) for item in items], "meta": {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit)}}


class LoanService:
    def __init__(self, db: Session):
        self.db = db

    def borrow(self, book_id: int, days: int, actor: User, now: datetime | None = None) -> Loan:
        if actor.role != Role.MEMBER:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only members can borrow books")
        book = self.db.scalar(select(Book).where(Book.id == book_id).with_for_update())
        if book is None or not book.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
        if book.available_copies < 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "No copies are available")
        current = now or datetime.now(timezone.utc)
        book.available_copies -= 1
        loan = Loan(member_id=actor.id, book_id=book.id, borrowed_at=current, due_at=current + timedelta(days=days))
        self.db.add(loan)
        self.db.flush()
        self.db.add(ActivityLog(user_id=actor.id, action="BORROW", entity_type="LOAN", entity_id=loan.id))
        commit_or_conflict(self.db, "Member already has an active loan for this book")
        self.db.refresh(loan)
        return loan

    def return_book(self, loan_id: int, actor: User, now: datetime | None = None) -> Loan:
        loan = self.db.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
        if loan is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Loan not found")
        if actor.role == Role.MEMBER and loan.member_id != actor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot return another member's loan")
        if loan.returned_at is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Loan is already returned")
        book = self.db.scalar(select(Book).where(Book.id == loan.book_id).with_for_update())
        if book is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Loan book no longer exists")
        loan.returned_at, loan.processed_by = now or datetime.now(timezone.utc), actor.id
        book.available_copies += 1
        self.db.add(ActivityLog(user_id=actor.id, action="RETURN", entity_type="LOAN", entity_id=loan.id))
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def list(self, actor: User, active: bool | None, page: int, limit: int) -> dict:
        query, count = select(Loan), select(func.count()).select_from(Loan)
        conditions = []
        if actor.role == Role.MEMBER:
            conditions.append(Loan.member_id == actor.id)
        if active is True:
            conditions.append(Loan.returned_at.is_(None))
        elif active is False:
            conditions.append(Loan.returned_at.is_not(None))
        items = self.db.scalars(query.where(*conditions).order_by(Loan.borrowed_at.desc()).offset((page - 1) * limit).limit(limit)).all()
        total = self.db.scalar(count.where(*conditions)) or 0
        return {"data": [LoanOut.model_validate(item) for item in items], "meta": {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit)}}

    def overdue(self, now: datetime | None = None) -> list[Loan]:
        current = now or datetime.now(timezone.utc)
        return list(self.db.scalars(select(Loan).where(Loan.returned_at.is_(None), Loan.due_at < current).order_by(Loan.due_at)).all())

