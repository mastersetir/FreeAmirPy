"""عملیات رمزنگاری: امضای RSA-SHA256 مطابق الزام مودیان."""
import base64
import json
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

def load_private_key(pem: str, password: str | None = None) -> rsa.RSAPrivateKey:
    data = pem.encode("utf-8")
    pw = password.encode("utf-8") if password else None
    return serialization.load_pem_private_key(data, password=pw)

def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def rsa_sha256_sign(private_key: rsa.RSAPrivateKey, data: bytes) -> bytes:
    return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())

def sign_packet(payload: dict, private_key_pem: str) -> str:
    key = load_private_key(private_key_pem)
    body = canonical_json(payload).encode("utf-8")
    signature = rsa_sha256_sign(key, body)
    return base64.b64encode(signature).decode("ascii")
