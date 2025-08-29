import jwt
import datetime

JWT_SECRET = "hiIamChamod"  # same as your env variable
JWT_ALGORITHM = "HS256"

payload = {
    "sub": "chamod",  # can be any user identifier
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # 1-hour expiry
}

token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
print(token)
