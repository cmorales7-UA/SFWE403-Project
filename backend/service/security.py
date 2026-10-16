import hashlib
import hmac
import secrets

def hash_secret(value):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'{salt}:{digest}'

def verify_secret(value, encoded):
    salt, digest = encoded.split(':')
    actual = hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, digest)

def public_user(user):
    return {k: v for k, v in user.items() if k not in {'password_hash', 'security_answer_1_hash', 'security_answer_2_hash'}}
