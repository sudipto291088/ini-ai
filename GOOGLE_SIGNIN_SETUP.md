# Google-only sign-in setup

Public visitor access remains enabled by default. Google sign-in is an opt-in
gate (`INI_GOOGLE_SIGNIN_ENABLED=1`), not yet a live requirement. When enabled,
the gate requires a verified Google account before reading chat storage or
rendering learning/chat UI. Do not enable it without configured credentials
and a verified real Google login round trip.

## Configure Google

1. Create/select your project in Google Cloud Console. Configure Google Auth
   Platform branding and audience for InI.ai. Use only basic OpenID, profile and
   email scopes; do not request Drive, Gmail, or other Google data access.
2. Create an OAuth client with application type **Web application**.
3. Register these authorized redirect URIs exactly:
   - Local: `http://localhost:8501/oauth2callback`
   - Hosted: `https://ini-ai-xqxyyydg65kq2fa73yz2gh.streamlit.app/oauth2callback`
4. If the Google application is in Testing, add intended tester accounts. Configure
   the production audience and any required Google checks before public rollout.

Official guide: https://developers.google.com/identity/openid-connect/openid-connect

## Configure InI

- Install the repository requirements; `streamlit[auth]` supplies Authlib.
- Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` locally.
- Enter the Google client ID and secret. Generate a random cookie secret of at
  least 64 characters (for example `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
- Keep actual credentials out of Git, chat messages, screenshots, and logs.
- On Streamlit Community Cloud, enter the same TOML in the app's private Secrets
  settings, using the hosted redirect URI instead of the local one.
- Restart after configuring secrets, then test Google login in a normal browser
  tab. Streamlit authentication does not support embedded apps.

## Ownership and existing history

Ownership uses Google's stable subject identifier, not email, visitor URL,
display name, or a user-supplied browser value. Streamlit/Authlib validates OIDC;
the app additionally enforces issuer, audience, verified email, and expiration
on each rerun. An expired identity must sign in again.

Existing anonymous records remain in the database. They are not deleted or
automatically claimed by a signed-in account: possession of an old URL does
not establish ownership. A separately authorized migration/recovery process
is needed to connect old history safely. No such migration is implemented.

Changing accounts clears in-memory chat/QC state. Chat read, rename, delete,
save and curriculum access retain the database's owner filters. Sign out clears
the current session and calls Streamlit logout; other already-open tabs have
Streamlit's documented independent-session behavior, not global revocation.

## Verification before rollout

- Complete real Google sign-in locally and on the hosted app.
- Verify accounts A and B cannot access each other's chats or curricula, including
  when account B pastes account A's chat URL.
- Verify logout, expiry, blocked/failed login and navigation after login.
- Verify the mobile sign-in view and first-time welcome flow.

Unit tests cover claims, state isolation, storage isolation and gate ordering.
They do not replace a real OAuth round-trip with configured Google credentials.
# Current access status

Public visitor access is restored by default while Google sign-in is unfinished.
This retains the previous URL-based visitor privacy limitation; do not treat it as account authentication.
The saved Google sign-in gate activates only when `INI_GOOGLE_SIGNIN_ENABLED=1` is explicitly set.
Do not enable it on the live deployment until credentials and a real login round trip have been verified.
