from app.core.security import get_password_hash, verify_password
hash = get_password_hash("infinity trader")
print("Hash:", hash)
print("Verify:", verify_password("infinity trader", hash))
