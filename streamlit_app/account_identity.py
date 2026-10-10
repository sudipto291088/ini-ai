"""Account ownership derived only from Streamlit-validated Google OIDC claims."""

import hashlib
import math
import time
from collections.abc import Mapping
from urllib.parse import urlsplit

GOOGLE_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}


def google_configured(secrets: Mapping) -> bool:
    """Validate configuration without exposing secret values or enabling a bypass."""
    auth = secrets.get("auth", {})
    if not isinstance(auth, Mapping):
        return False
    google = auth.get("google", {})
    if not isinstance(google, Mapping):
        return False
    required = (auth.get("cookie_secret"), google.get("client_id"), google.get("client_secret"))
    if any(not isinstance(value, str) or not value.strip() or "REPLACE" in value for value in required):
        return False
    if len(auth["cookie_secret"]) < 64 or google.get("server_metadata_url") != GOOGLE_METADATA_URL:
        return False
    redirect = urlsplit(str(auth.get("redirect_uri", "")))
    if not redirect.hostname or redirect.path != "/oauth2callback" or redirect.query or redirect.fragment or redirect.username:
        return False
    return redirect.scheme == "https" or (
        redirect.scheme == "http" and redirect.hostname in {"localhost", "127.0.0.1"}
    )


def google_owner_id(claims: Mapping, client_id: str, now: float | None = None) -> str | None:
    """Accept only server-validated st.user data; never a URL or browser payload.

    Streamlit/Authlib performs signature, state, nonce and OIDC validation.
    These additional checks enforce provider, audience and expiry on each rerun.
    Email is not used as the stable ownership key.
    """
    if claims.get("is_logged_in") is not True or claims.get("iss") not in GOOGLE_ISSUERS:
        return None
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if not client_id or client_id not in audiences:
        return None
    if len(audiences) > 1 and claims.get("azp") != client_id:
        return None
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
        return None
    if claims.get("email_verified") is not True:
        return None
    try:
        expiration = float(claims.get("exp", 0))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(expiration) or expiration <= (time.time() if now is None else now):
        return None
    digest = hashlib.sha256(("https://accounts.google.com\0" + subject).encode()).hexdigest()
    return "google-" + digest


def bind_account_state(state, owner_id: str) -> None:
    """Discard prior-account/anonymous in-memory chat data on an identity change."""
    if state.get("_authenticated_owner") != owner_id:
        state.clear()
        state["_authenticated_owner"] = owner_id
    # Keep the existing storage API name; its value is now a verified account key.
    state["visitor_id"] = owner_id
