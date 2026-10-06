from sqlalchemy import select

from app.auth import hash_password
from app.database import SessionLocal
from app.models import Book, Role, User


def make_user(db, name: str, email: str, password: str, role: Role) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        db.add(user); db.flush()
    return user


def main() -> None:
    with SessionLocal() as db:
        admin = make_user(db, "Development Admin", "admin@example.com", "AdminPassword123!", Role.ADMIN)
        make_user(db, "Development Librarian", "librarian@example.com", "LibrarianPassword123!", Role.LIBRARIAN)
        make_user(db, "Development Member", "member@example.com", "MemberPassword123!", Role.MEMBER)
        if db.scalar(select(Book).where(Book.isbn == "9780132350884")) is None:
            db.add(Book(isbn="9780132350884", title="Clean Code", author="Robert C. Martin", description="A handbook of agile software craftsmanship.", total_copies=3, available_copies=3, created_by=admin.id, updated_by=admin.id))
        db.commit()
    print("development seed complete")


if __name__ == "__main__":
    main()

