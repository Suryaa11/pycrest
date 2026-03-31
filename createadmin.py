import sys
import os
from datetime import datetime

# 1. Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'auth-service'))

# 2. Set Environment Variables BEFORE importing app modules
os.environ["MONGODB_URI"] = "mongodb://pycrest:pycrest123@paycrest-mongodb:27017/pycrest?authSource=admin"
os.environ["MONGODB_DB"] = "pycrest"

# 3. Now import your app's database and security logic
import asyncio
from getpass import getpass
from app.database.mongo import get_db
from app.core.security import hash_password

async def create_admin(email: str, full_name: str, password: str):
    db = await get_db()
    existing = await db.staff_users.find_one({"email": email}) or await db.users.find_one({"email": email})
    if existing:
        print(f"User with email {email} already exists (id={existing.get('_id')}).")
        return
    doc = {
        "full_name": full_name,
        "email": email,
        "password": hash_password(password),
        "phone": None,
        "dob": None,
        "gender": None,
        "pan_number": None,
        "role": Roles.ADMIN,
        "_id": await next_customer_id(),
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    res = await db.staff_users.insert_one(doc)
    print(f"Created admin user: {email} (id={doc.get('_id')})")


def main():
    print("Create initial admin user for PAY CREST")
    email = input("Admin email: ")
    full_name = input("Full name: ")
    password = getpass("Password (hidden): ")
    password2 = getpass("Confirm password: ")
    if password != password2:
        print("Passwords do not match")
        return
    asyncio.run(create_admin(email, full_name, password))


if __name__ == '__main__':
    main()