from features.user._pure import normalize_email, validate_name
from features.user.protocol import UserRepository
from features.user.types import User


def list_users(repo: UserRepository) -> list[User]:
    return repo.list_all()


def create_user(repo: UserRepository, *, name: str, email: str) -> User:
    validate_name(name)
    return repo.create(name=name.strip(), email=normalize_email(email))
