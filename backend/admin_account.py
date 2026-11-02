import argparse
from datetime import datetime
from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, migrate_admin_password_rotation
from app.core.security import hash_password, verify_password
from app.models import all_models  # noqa: F401
from app.models.all_models import PasswordHistory, Role, User
from app.services.activity import record_activity


def validate_password(password: str) -> None:
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must contain at least {settings.PASSWORD_MIN_LENGTH} characters."
        )
    if not any(char.islower() for char in password):
        raise ValueError("Password must include a lower-case letter.")
    if not any(char.isupper() for char in password):
        raise ValueError("Password must include an upper-case letter.")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must include a number.")
    if not any(not char.isalnum() for char in password):
        raise ValueError("Password must include a special character.")


def _prompt_password() -> str:
    for _ in range(3):
        password = getpass("New administrator password: ")
        confirmation = getpass("Confirm administrator password: ")
        if password != confirmation:
            print("Passwords do not match.")
            continue
        try:
            validate_password(password)
        except ValueError as exc:
            print(str(exc))
            continue
        return password
    raise RuntimeError("Password setup failed after three attempts.")


def create_initial_admin(db: Session, password: str) -> User:
    validate_password(password)
    existing_admin = (
        db.query(User)
        .join(Role)
        .filter(Role.role_name.in_(("SUPER_ADMIN", "ADMIN")))
        .first()
    )
    if existing_admin:
        raise ValueError(
            "An administrator already exists. Use the reset command instead."
        )
    if db.query(User).filter(
        or_(User.username == "admin", User.email == "admin@smartparking.local")
    ).first():
        raise ValueError("The initial administrator username or email is already in use.")

    role = db.query(Role).filter_by(role_name="SUPER_ADMIN").first()
    if not role:
        role = Role(role_name="SUPER_ADMIN", description="Full access")
        db.add(role)
        db.flush()
    user = User(
        username="admin",
        email="admin@smartparking.local",
        full_name="System Administrator",
        role_id=role.role_id,
        password_hash=hash_password(password),
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    record_activity(
        db,
        user.user_id,
        "ADMIN_BOOTSTRAPPED",
        "USER",
        user.user_id,
        {"source": "local_cli", "must_change_password": True},
    )
    db.commit()
    return user


def reset_admin_password(
    db: Session,
    username: str,
    password: str,
    require_rotation: bool = False,
) -> User:
    validate_password(password)
    user = (
        db.query(User)
        .join(Role)
        .filter(
            User.username == username,
            Role.role_name.in_(("SUPER_ADMIN", "ADMIN")),
        )
        .with_for_update()
        .first()
    )
    if not user:
        raise ValueError("No administrator with that username exists.")
    if not user.is_active:
        raise ValueError("The administrator account is inactive; it was not changed.")

    previous_hashes = [user.password_hash]
    previous_hashes.extend(
        row.password_hash
        for row in db.query(PasswordHistory)
        .filter_by(user_id=user.user_id)
        .order_by(PasswordHistory.history_id.desc())
        .limit(5)
        .all()
    )
    if any(verify_password(password, old_hash) for old_hash in previous_hashes):
        raise ValueError("Password must not reuse one of the six most recent passwords.")

    previous_hash = user.password_hash
    user.password_hash = hash_password(password)
    user.password_version += 1
    user.password_changed_at = datetime.utcnow()
    user.must_change_password = user.must_change_password or require_rotation
    db.add(PasswordHistory(user_id=user.user_id, password_hash=previous_hash))
    db.flush()
    stale_history_ids = [
        row.history_id
        for row in db.query(PasswordHistory.history_id)
        .filter_by(user_id=user.user_id)
        .order_by(PasswordHistory.history_id.desc())
        .offset(5)
        .all()
    ]
    if stale_history_ids:
        db.query(PasswordHistory).filter(
            PasswordHistory.history_id.in_(stale_history_ids)
        ).delete(synchronize_session=False)
    record_activity(
        db,
        user.user_id,
        "ADMIN_PASSWORD_RESET",
        "USER",
        user.user_id,
        {
            "source": "local_cli",
            "must_change_password": user.must_change_password,
            "outcome": "SUCCESS",
        },
    )
    db.commit()
    return user


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Securely initialize or reset an administrator account."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "bootstrap",
        help="Create the first administrator if no administrator exists.",
    )
    reset_parser = commands.add_parser(
        "reset",
        help="Reset an existing administrator password.",
    )
    reset_parser.add_argument("--username", default="admin")
    reset_parser.add_argument(
        "--require-rotation",
        action="store_true",
        help="Require a further password change at next sign-in.",
    )
    args = parser.parse_args()

    try:
        Base.metadata.create_all(bind=engine)
        migrate_admin_password_rotation(engine)
    except SQLAlchemyError as exc:
        raise RuntimeError(
            f"Database initialization failed ({type(exc).__name__}); check the local database service and configuration."
        ) from None
    password = _prompt_password()
    try:
        with SessionLocal() as db:
            if args.command == "bootstrap":
                user = create_initial_admin(db, password)
                print(f"Administrator {user.username!r} created; password rotation is required.")
            else:
                user = reset_admin_password(
                    db,
                    args.username,
                    password,
                    require_rotation=args.require_rotation,
                )
                print(f"Password reset for administrator {user.username!r}; existing tokens are revoked.")
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")
    except SQLAlchemyError as exc:
        raise RuntimeError(
            f"Administrator account operation failed ({type(exc).__name__}); check the local database service and configuration."
        ) from None


if __name__ == "__main__":
    main()
