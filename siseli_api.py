#!/usr/bin/env python3
"""Siseli/Fronus Solar API client with HMAC signing."""

import hashlib
import hmac
import json
import random
import string
import requests
from urllib.parse import urlparse, parse_qs, urlencode

BASE_URL = "https://solar.siseli.com/apis"
APP_ID = "rBrTRfAPXz"
APP_SECRET_ENC = "I4D0KRr2339z3pQ/at91V9BpFAOe54DaTafwSm6suIQ="


def md5_hex(data: str) -> str:
    """Compute MD5 hash and return lowercase hex."""
    return hashlib.md5(data.encode()).hexdigest().lower()


def generate_nonce(length: int = 32) -> str:
    """Generate random nonce string."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def compute_body_hash(body: str = "", method: str = "GET") -> str:
    """
    Compute body hash (Ge function).
    For non-GET requests with string body: MD5 of parsed body, lowercase.
    For GET requests: empty string.
    """
    if method.upper() == "GET" or not body:
        return ""
    # The JS does: CryptoJS.MD5(CryptoJS.enc.Utf8.parse(body)).toString().toLowerCase()
    return md5_hex(body)


def decrypt_app_secret(app_id: str, encrypted_secret: str) -> str:
    """
    Decrypt appSecret (qe function in JS).
    JS: MD5(appId).toLowerCase() -> first 16 chars = key, last 16 chars = IV
        AES-CBC decrypt(encrypted_secret, key, IV) with ZeroPadding
    """
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    import base64

    app_id_md5 = md5_hex(app_id)
    key = app_id_md5[:16].encode()
    iv = app_id_md5[16:].encode()

    encrypted_bytes = base64.b64decode(encrypted_secret)
    cipher = AES.new(key, AES.MODE_CBC, iv)

    try:
        decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
    except ValueError:
        # ZeroPadding - strip trailing null bytes
        decrypted = cipher.decrypt(encrypted_bytes).rstrip(b'\x00')

    return decrypted.decode('utf-8').strip()


def compute_sign(params: dict, secret: str) -> str:
    """
    Compute IOT-Open-Sign (Ye function in JS).
    
    JS: 
      1. qs.sortKeys().all() - sort params by key
      2. stringify with encode:false 
      3. parse as query string
      4. stringify back (this normalizes)
      5. HmacSHA256(normalized_string, secret)
      6. MD5 of the HMAC result, lowercase
    """
    # Sort by key
    sorted_params = dict(sorted(params.items()))
    # URL encode without special encoding
    query = urlencode(sorted_params, doseq=False)
    # The JS does encode:false then re-parses, which normalizes
    # Effectively: sort keys, join as key=value&key=value
    # Then HMAC-SHA256 with secret, then MD5
    hmac_result = hmac.new(
        secret.encode(),
        query.encode(),
        hashlib.sha256
    ).hexdigest().lower()
    
    # Final: MD5 of HMAC result
    return md5_hex(hmac_result)


def build_headers(method: str, url: str, body: str = "", access_token: str = "") -> dict:
    """Build all required IOT headers for a request."""
    nonce = generate_nonce(32)
    body_hash = compute_body_hash(body, method)
    
    # Use pre-decrypted secret
    secret = "CJbrtLtqFES62bJ3ZW7c"
    
    # Build params dict from URL query string + body hash + appID + nonce
    parsed = urlparse(url)
    params = {}
    if parsed.query:
        for k, v in parse_qs(parsed.query, keep_blank_values=True).items():
            params[k] = v[0] if len(v) == 1 else v
    
    # Add signing params
    params["IOT-Open-AppID"] = APP_ID
    params["IOT-Open-Nonce"] = nonce
    if body_hash:
        params["IOT-Open-Body-Hash"] = body_hash
    
    # Compute sign
    sign = compute_sign(params, secret)
    
    headers = {
        "IOT-Open-AppID": APP_ID,
        "IOT-Open-Nonce": nonce,
        "IOT-Open-Sign": sign,
        "IOT-Open-Body-Hash": body_hash,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    
    return headers


def login(username: str, password: str) -> dict:
    """Login and get access token."""
    # First hash the password as MD5
    body = json.dumps({"account": username, "password": md5_hex(password)})
    url = f"{BASE_URL}/login/account"
    headers = build_headers("POST", url, body)
    resp = requests.post(url, headers=headers, data=body, timeout=15)
    return resp.json()


def get_stations(access_token: str) -> dict:
    """Get station list."""
    url = f"{BASE_URL}/station/list"
    headers = build_headers("GET", url, access_token=access_token)
    resp = requests.get(url, headers=headers, timeout=15)
    return resp.json()


def get_station_details(access_token: str, station_id: str) -> dict:
    """Get station details."""
    url = f"{BASE_URL}/station/details?stationId={station_id}"
    headers = build_headers("GET", url, access_token=access_token)
    resp = requests.get(url, headers=headers, timeout=15)
    return resp.json()


def get_energy_daily(access_token: str, station_id: str) -> dict:
    """Get daily energy generation."""
    url = f"{BASE_URL}/stationOverView/generatedEnergy/daily?stationId={station_id}"
    headers = build_headers("GET", url, access_token=access_token)
    resp = requests.get(url, headers=headers, timeout=15)
    return resp.json()


def get_generation_power(access_token: str, station_id: str) -> dict:
    """Get current generation power."""
    url = f"{BASE_URL}/stationOverView/generationPower/daily?stationId={station_id}"
    headers = build_headers("GET", url, access_token=access_token)
    resp = requests.get(url, headers=headers, timeout=15)
    return resp.json()


if __name__ == "__main__":
    import sys
    
    # Quick test: decrypt and show secret
    secret = decrypt_app_secret(APP_ID, APP_SECRET_ENC)
    print(f"Decrypted appSecret: {secret}")
    print(f"AppID: {APP_ID}")
    print()
    
    if len(sys.argv) >= 3:
        user, pw = sys.argv[1], sys.argv[2]
        print(f"Logging in as {user}...")
        result = login(user, pw)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python3 siseli_api.py <account> <password>")
        print("  Login credentials from the Sun House app")