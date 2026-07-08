import base64, hashlib, hmac, json, os, time
from typing import Optional
SECRET = os.getenv('BBLOTTO_SECRET', 'CHANGE_ME_BBLOTTO_V50_SECRET')
def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 120000).hex()
    return f'pbkdf2_sha256${salt}${digest}'
def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split('$')
        calc = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 120000).hex()
        return hmac.compare_digest(calc, digest)
    except Exception:
        return False
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')
def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
def create_token(admin_id: int, username: str, role: str = 'admin', ttl: int = 60*60*8) -> str:
    header = {'alg':'HS256','typ':'JWT'}
    payload = {'sub':admin_id,'username':username,'role':role,'exp':int(time.time()+ttl)}
    signing = f"{_b64(json.dumps(header,separators=(',',':')).encode())}.{_b64(json.dumps(payload,separators=(',',':')).encode())}"
    sig = hmac.new(SECRET.encode(), signing.encode(), hashlib.sha256).digest()
    return signing + '.' + _b64(sig)
def verify_token(token: str) -> Optional[dict]:
    try:
        a,b,c = token.split('.')
        signing=f'{a}.{b}'
        sig=_b64(hmac.new(SECRET.encode(), signing.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig,c): return None
        payload=json.loads(_unb64(b))
        if payload.get('exp',0) < time.time(): return None
        return payload
    except Exception:
        return None
