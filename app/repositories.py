from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Book


class BookRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, search: str, available: bool | None, page: int, limit: int):
        query = select(Book).where(Book.is_active.is_(True))
        count = select(func.count()).select_from(Book).where(Book.is_active.is_(True))
        conditions = []
        if search:
            conditions.append(or_(Book.title.ilike(f"%{search}%"), Book.author.ilike(f"%{search}%"), Book.isbn.ilike(f"%{search}%")))
        if available is True:
            conditions.append(Book.available_copies > 0)
        elif available is False:
            conditions.append(Book.available_copies == 0)
        items = self.db.scalars(query.where(*conditions).order_by(Book.title, Book.id).offset((page - 1) * limit).limit(limit)).all()
        return list(items), self.db.scalar(count.where(*conditions)) or 0

