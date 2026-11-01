"""Create a staff account on an existing database, for example the first admin.

    python backend/create_staff.py --name "Asha Rao" --email asha@company.com --role admin

The password is asked for on the command line and is not echoed. Roles: admin, sales, technician, support, warehouse.
A technician account is linked to a new technician record, or to an existing one with --technician-id.
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from backend.app.core.database import Base, SessionLocal, engine
from backend.app.core.roles import STAFF_ROLES
from backend.app.services.user_service import create_staff_user


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a staff account.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=STAFF_ROLES)
    parser.add_argument("--phone")
    parser.add_argument("--technician-id", type=int)
    args = parser.parse_args()

    password = getpass.getpass("Password (at least 8 characters): ")
    if len(password) < 8:
        print("The password must be at least 8 characters.")
        return 1
    if password != getpass.getpass("Repeat the password: "):
        print("The passwords do not match.")
        return 1

    Base.metadata.create_all(bind=engine)  # makes sure the users table exists
    db = SessionLocal()
    try:
        user = create_staff_user(
            db, args.name, args.email, password, args.role, phone=args.phone, technician_id=args.technician_id
        )
        print(f"Created {user.role} account for {user.email}.")
        return 0
    except HTTPException as err:
        print(f"Could not create the account: {err.detail}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
