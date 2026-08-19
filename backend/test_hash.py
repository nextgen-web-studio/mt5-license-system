from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hash = pwd_context.hash("infinity trader")
print("Hash:", hash)
print("Verify:", pwd_context.verify("infinity trader", hash))
