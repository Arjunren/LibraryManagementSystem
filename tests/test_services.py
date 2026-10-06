from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models import Book, Role, User
from app.services import LoanService


def setup(db, copies=1):
    admin = User(name="Admin", email="admin@example.com", password_hash="x", role=Role.ADMIN)
    member = User(name="Member", email="member@example.com", password_hash="x", role=Role.MEMBER)
    other = User(name="Other", email="other@example.com", password_hash="x", role=Role.MEMBER)
    db.add_all([admin, member, other]); db.flush()
    book = Book(isbn="9780132350884", title="Clean Code", author="Robert Martin", total_copies=copies, available_copies=copies, created_by=admin.id, updated_by=admin.id)
    db.add(book); db.commit()
    return admin, member, other, book


def test_borrow_and_return_updates_inventory(db):
    _admin, member, _other, book = setup(db)
    service = LoanService(db)
    loan = service.borrow(book.id, 14, member)
    assert book.available_copies == 0
    service.return_book(loan.id, member)
    assert book.available_copies == 1


def test_cannot_borrow_unavailable_or_duplicate_book(db):
    _admin, member, _other, book = setup(db)
    service = LoanService(db)
    service.borrow(book.id, 14, member)
    with pytest.raises(HTTPException) as error:
        service.borrow(book.id, 14, member)
    assert error.value.status_code == 409


def test_member_cannot_return_another_members_loan(db):
    _admin, member, other, book = setup(db)
    loan = LoanService(db).borrow(book.id, 14, member)
    with pytest.raises(HTTPException) as error:
        LoanService(db).return_book(loan.id, other)
    assert error.value.status_code == 403


def test_overdue_report(db):
    _admin, member, _other, book = setup(db)
    then = datetime(2026, 1, 1, tzinfo=timezone.utc)
    LoanService(db).borrow(book.id, 1, member, then)
    assert len(LoanService(db).overdue(then + timedelta(days=2))) == 1

