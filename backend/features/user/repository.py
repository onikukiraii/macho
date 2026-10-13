from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common.db.entities import UserRow
from common.errors import Conflict
from features.user.types import User


class DbUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[User]:
        rows = self._session.execute(select(UserRow).order_by(UserRow.id)).scalars().all()
        return [_to_domain(row) for row in rows]

    def create(self, *, name: str, email: str) -> User:
        row = UserRow(name=name, email=email)
        self._session.add(row)
        try:
            self._session.commit()
        except IntegrityError as e:
            self._session.rollback()
            raise Conflict(f"email はすでに登録されています: email={email}") from e
        self._session.refresh(row)
        return _to_domain(row)


def _to_domain(row: UserRow) -> User:
    return User(id=row.id, name=row.name, email=row.email, created_at=row.created_at)
