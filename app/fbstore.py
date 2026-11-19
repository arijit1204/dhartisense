"""Firebase back end: accounts and fields.

Firebase Authentication does the account work: it stores passwords, sends the verification and password-reset emails (free), and throttles abuse.
The browser signs in with the Firebase web SDK and hands the resulting ID token to /api/auth/session. The server checks it, requires a verified email,
and swaps it for a Firebase session cookie (HttpOnly, 14 days). Fields live in Firestore at users/{uid}/fields/{id}, written only by this server
(the Firestore rules deny every direct browser access).

Settings (environment or .env):
  FIREBASE_PROJECT_ID, FIREBASE_API_KEY            from Project settings > General > Web app
  FIREBASE_SERVICE_ACCOUNT_FILE or _JSON           service-account key (use the JSON variant on a host without files)
  FIREBASE_AUTH_DOMAIN                             optional, defaults to <project>.firebaseapp.com
For local development against the Firebase emulators set FIREBASE_AUTH_EMULATOR_HOST (and FIRESTORE_EMULATOR_HOST). DHARTISENSE_FIRESTORE=memory
keeps fields in memory instead of Firestore; it exists for tests and is lost on restart.
"""

import datetime
import json
import os
import re
import threading
import time
import uuid

import firebase_admin
from firebase_admin import auth, credentials

SESSION_DAYS = 14  # the longest a Firebase session cookie can last
MAX_FIELDS = 50
MAX_FIELD_BYTES = 300_000  # a field with its boundary, observations and last plans is a few KB; this stops abuse
FIELD_ID = re.compile(r"^[A-Za-z0-9]{1,40}$")  # Firestore auto ids; keeps a crafted id from reaching another path
RECENT_SIGN_IN_SECONDS = 3600  # a session is only issued from a sign-in made within the last hour (it can take a while to open the verification email)
_lock = threading.Lock()
_app = None
_fields = None


def configured() -> bool:
    return bool(os.getenv("FIREBASE_PROJECT_ID") and os.getenv("FIREBASE_API_KEY"))


def web_config() -> dict:
    """What the browser needs to start the Firebase web SDK. The API key is public by design; Firebase protects data with rules and server checks."""
    project = os.getenv("FIREBASE_PROJECT_ID", "")
    emulator = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
    return {"configured": configured(), "apiKey": os.getenv("FIREBASE_API_KEY", ""), "projectId": project,
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN") or f"{project}.firebaseapp.com", "authEmulator": f"http://{emulator}" if emulator else None}


def _init():
    global _app, _fields
    with _lock:
        if _app is not None:
            return
        raw, path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"), os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
        cred = credentials.Certificate(json.loads(raw)) if raw else credentials.Certificate(path) if path else None
        _app = firebase_admin.initialize_app(cred, {"projectId": os.getenv("FIREBASE_PROJECT_ID")})
        _fields = MemoryFields() if (os.getenv("DHARTISENSE_FIRESTORE") or os.getenv("FARMCONTEXT_FIRESTORE")) == "memory" else FirestoreFields()


# ---- sessions ----

class SignInError(Exception):
    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def create_session(id_token: str):
    """Check a fresh Firebase ID token and return (session cookie, user)."""
    _init()
    try:
        decoded = auth.verify_id_token(id_token, check_revoked=True)
    except Exception as error:  # expired, forged, revoked or malformed: all mean "not signed in"
        raise SignInError("Sign-in could not be checked. Try again.") from error
    if not decoded.get("email_verified"):
        raise SignInError("Confirm your email first.", "unverified")
    if time.time() - decoded.get("auth_time", 0) > RECENT_SIGN_IN_SECONDS:
        raise SignInError("Please sign in again.", "stale")
    cookie = auth.create_session_cookie(id_token, expires_in=datetime.timedelta(days=SESSION_DAYS))
    return cookie, _user(decoded)


def _user(claims: dict) -> dict:
    email = claims.get("email") or ""
    return {"id": claims["uid"], "email": email, "name": claims.get("name") or email.split("@")[0], "verified": bool(claims.get("email_verified"))}


def user_for(cookie: str):
    if not cookie:
        return None
    _init()
    try:
        return _user(auth.verify_session_cookie(cookie, check_revoked=False))  # shortcut: skips the per-request revocation lookup; sign-out revokes at the next token refresh
    except Exception:
        return None


def end_session(cookie: str) -> None:
    """Sign out everywhere: revoke the account's refresh tokens so other devices must sign in again after their cookie expires."""
    if not cookie:
        return
    _init()
    try:
        auth.revoke_refresh_tokens(auth.verify_session_cookie(cookie)["uid"])
    except Exception:
        pass


# ---- fields ----

def _clean(data):
    if not isinstance(data, dict):
        return None, "Field data must be an object."
    body = {k: v for k, v in data.items() if k not in ("id", "updatedAt")}
    raw = json.dumps(body)
    if len(raw) > MAX_FIELD_BYTES:
        return None, "This field's data is too large."
    return (body, raw), None


class MemoryFields:
    def __init__(self):
        self.rows = {}

    def list(self, uid):
        return sorted(((i, r) for (u, i), r in self.rows.items() if u == uid), key=lambda x: -x[1]["updated_at"])

    def create(self, uid, name, raw):
        fid = uuid.uuid4().hex[:20]
        self.rows[(uid, fid)] = {"name": name, "data": raw, "updated_at": time.time()}
        return fid

    def update(self, uid, fid, name, raw):
        if (uid, fid) not in self.rows:
            return False
        self.rows[(uid, fid)] = {"name": name, "data": raw, "updated_at": time.time()}
        return True

    def delete(self, uid, fid):
        return self.rows.pop((uid, fid), None) is not None


class FirestoreFields:
    def __init__(self):
        from firebase_admin import firestore

        self.db = firestore.client()
        self.firestore = firestore

    def _col(self, uid):
        return self.db.collection("users").document(uid).collection("fields")

    def list(self, uid):
        docs = self._col(uid).order_by("updated_at", direction=self.firestore.Query.DESCENDING).stream()
        return [(d.id, {**d.to_dict(), "updated_at": d.to_dict()["updated_at"].timestamp()}) for d in docs]

    def create(self, uid, name, raw):
        ref = self._col(uid).document()
        ref.set({"name": name, "data": raw, "updated_at": datetime.datetime.now(datetime.timezone.utc)})
        return ref.id

    def update(self, uid, fid, name, raw):
        ref = self._col(uid).document(fid)
        if not ref.get().exists:
            return False
        ref.update({"name": name, "data": raw, "updated_at": datetime.datetime.now(datetime.timezone.utc)})
        return True

    def delete(self, uid, fid):
        ref = self._col(uid).document(fid)
        if not ref.get().exists:
            return False
        ref.delete()
        return True


def _out(fid, row):
    return {**json.loads(row["data"]), "id": fid, "updatedAt": datetime.datetime.fromtimestamp(row["updated_at"], datetime.timezone.utc).isoformat()}


def list_fields(uid: str) -> list:
    _init()
    return [_out(i, r) for i, r in _fields.list(uid)]


def save_field(uid: str, field_id, data):
    """Create (field_id None) or update one of this user's own fields. Returns (field, error)."""
    cleaned, error = _clean(data)
    if error:
        return None, error
    body, raw = cleaned
    name = str(body.get("fieldName") or "").strip()[:120] or "Unnamed field"
    _init()
    if field_id is None:
        if len(_fields.list(uid)) >= MAX_FIELDS:
            return None, f"You can keep up to {MAX_FIELDS} fields."
        field_id = _fields.create(uid, name, raw)
    elif not FIELD_ID.match(str(field_id)) or not _fields.update(uid, str(field_id), name, raw):
        return None, "Field not found."
    return _out(field_id, {"data": raw, "updated_at": time.time()}), None


def delete_field(uid: str, field_id) -> bool:
    _init()
    return bool(FIELD_ID.match(str(field_id))) and _fields.delete(uid, str(field_id))


if __name__ == "__main__":  # self-check of the field layer on the in-memory store (sessions are covered by the emulator test)
    os.environ["DHARTISENSE_FIRESTORE"] = "memory"
    os.environ["FIREBASE_PROJECT_ID"] = "demo-test"
    f, err = save_field("alice", None, {"fieldName": "North", "areaHa": 1.2, "polygon": [[1, 1], [1, 2], [2, 2]]})
    assert f and not err and isinstance(f["id"], str), err
    assert save_field("bob", f["id"], {"fieldName": "hijack"})[0] is None  # not bob's
    assert not delete_field("bob", f["id"]) and list_fields("bob") == []
    assert save_field("alice", f["id"], {"fieldName": "North 2"})[0]["fieldName"] == "North 2"
    assert save_field("alice", "../other/fields/x", {"fieldName": "x"})[0] is None and not delete_field("alice", "a/b")
    assert [x["fieldName"] for x in list_fields("alice")] == ["North 2"] and delete_field("alice", f["id"]) and list_fields("alice") == []
    assert save_field("alice", None, {"fieldName": "x" * 400_000})[0] is None
    for _ in range(MAX_FIELDS):
        save_field("carol", None, {"fieldName": "f"})
    assert "up to" in save_field("carol", None, {"fieldName": "one too many"})[1]
    print("fbstore field layer self-check passed")
