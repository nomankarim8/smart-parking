from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from admin_account import create_initial_admin, reset_admin_password
from app.core.database import Base
from app.core.security import hash_password, verify_password
from app.models.all_models import ActivityLog, PasswordHistory, Role, User


@pytest.fixture
def admin_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        yield db
    engine.dispose()


def test_initial_admin_bootstrap_is_audited_and_requires_rotation(admin_db):
    user = create_initial_admin(admin_db, "SecureBootstrapPass1!")

    assert user.username == "admin"
    assert user.role.role_name == "SUPER_ADMIN"
    assert user.is_active is True
    assert user.must_change_password is True
    assert admin_db.query(ActivityLog).filter_by(
        action="ADMIN_BOOTSTRAPPED"
    ).count() == 1


def test_initial_admin_bootstrap_refuses_to_create_a_second_admin(admin_db):
    role = Role(role_name="ADMIN", description="Existing administrator")
    admin_db.add(role)
    admin_db.flush()
    admin_db.add(
        User(
            username="existing-admin",
            email="existing-admin@example.test",
            password_hash=hash_password("ExistingAdminPass1!"),
            full_name="Existing Admin",
            role_id=role.role_id,
        )
    )
    admin_db.commit()

    with pytest.raises(ValueError, match="administrator already exists"):
        create_initial_admin(admin_db, "AnotherSecurePass2!")

    assert admin_db.query(User).count() == 1


def test_admin_password_reset_rotates_password_and_revokes_existing_tokens(admin_db):
    role = Role(role_name="SUPER_ADMIN", description="Test administrator")
    admin_db.add(role)
    admin_db.flush()
    user = User(
        username="admin",
        email="admin@example.test",
        password_hash=hash_password("OriginalAdminPass1!"),
        full_name="Test Admin",
        role_id=role.role_id,
        must_change_password=True,
        password_version=3,
    )
    admin_db.add(user)
    admin_db.commit()

    reset_admin_password(
        admin_db,
        "admin",
        "ReplacementAdminPass2!",
    )

    admin_db.refresh(user)
    assert verify_password("ReplacementAdminPass2!", user.password_hash)
    assert user.password_version == 4
    assert isinstance(user.password_changed_at, datetime)
    assert user.must_change_password is True
    assert admin_db.query(PasswordHistory).filter_by(user_id=user.user_id).count() == 1
    assert admin_db.query(ActivityLog).filter_by(
        action="ADMIN_PASSWORD_RESET"
    ).count() == 1


def test_admin_password_reset_rejects_reuse_and_inactive_accounts(admin_db):
    role = Role(role_name="ADMIN", description="Test administrator")
    admin_db.add(role)
    admin_db.flush()
    user = User(
        username="admin",
        email="admin@example.test",
        password_hash=hash_password("OriginalAdminPass1!"),
        full_name="Test Admin",
        role_id=role.role_id,
    )
    admin_db.add(user)
    admin_db.commit()

    with pytest.raises(ValueError, match="must not reuse"):
        reset_admin_password(admin_db, "admin", "OriginalAdminPass1!")

    user.is_active = False
    admin_db.commit()
    with pytest.raises(ValueError, match="inactive"):
        reset_admin_password(admin_db, "admin", "ReplacementAdminPass2!")
