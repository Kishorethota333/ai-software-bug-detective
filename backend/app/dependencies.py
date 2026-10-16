from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models import User
from app.security import decode_token
security = HTTPBearer(auto_error=False)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try: payload = decode_token(credentials.credentials); user_id = int(payload.get("sub", "0"))
    except (ValueError, TypeError): raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if not user: raise HTTPException(status_code=401, detail="User no longer exists")
    return user

def require_roles(*roles):
    def checker(user: User = Depends(current_user)) -> User:
        if user.role not in roles: raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker
