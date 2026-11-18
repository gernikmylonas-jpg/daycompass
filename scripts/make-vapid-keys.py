"""Creates the key pair web push needs. Run once, then put the three lines in your .env:
    cd backend && venv\\Scripts\\python ..\\scripts\\make-vapid-keys.py
Keep the private key secret (never commit it)."""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid

v = Vapid()
v.generate_keys()
b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
public = b64(v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
private = b64(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
print("VAPID_PUBLIC_KEY=" + public)
print("VAPID_PRIVATE_KEY=" + private)
print("VAPID_SUBJECT=mailto:you@example.com   # an address of yours; push services may contact it")
