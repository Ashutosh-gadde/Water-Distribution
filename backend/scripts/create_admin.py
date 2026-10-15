"""Bootstrap the first Super Administrator. Password is prompted, never hardcoded.
Usage: python -m scripts.create_admin   (from the backend/ directory)"""
import getpass
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password, validate_password_strength
from app.models import User


def main():
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.role == "super_admin")):
            sys.exit("A Super Administrator already exists. Use the admin UI/API instead.")
        emp = input("Employee ID: ").strip()
        name = input("Full name: ").strip()
        pw = getpass.getpass("Password: ")
        if getpass.getpass("Confirm: ") != pw:
            sys.exit("Passwords do not match.")
        if (err := validate_password_strength(pw)):
            sys.exit(err)
        db.add(User(employee_id=emp, full_name=name, role="super_admin", password_hash=hash_password(pw)))
        db.commit()
        print("Super Administrator created.")


if __name__ == "__main__":
    main()
