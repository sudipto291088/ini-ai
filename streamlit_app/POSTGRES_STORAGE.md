# PostgreSQL storage rollout

The production entry point continues to default to SQLite. Only the isolated
`auth_test_app.py` entry point enables PostgreSQL when its private Streamlit
Secrets contains a top-level `INI_DATABASE_URL` value.

Do not put database credentials in source code, chat, screenshots or Git.
The URL belongs in private deployment Secrets. Local developer storage stays
unchanged unless `INI_STORAGE_BACKEND=postgres` is explicitly configured.

The backend stores both chat messages and full question-curriculum state.
Reads, listings, renames, deletes and upserts keep the existing owner predicates.
The owner comes from the verified Google identity, not the URL's visitor value.
User values use bound SQL parameters; database failures never trigger a fallback
to disposable local storage. TLS verifies the server certificate and hostname
using the certifi CA bundle.

The pool has at most five connections; statement and lock timeouts are applied
within each transaction for Neon transaction-pooling compatibility. Only schema
initialization is cached, not user records.

## Verification

Run the ordinary suite with `python -m unittest tests.test_storage_postgres
tests.test_storage_privacy tests.test_auth_test_engine tests.test_google_signin
tests.test_account_identity` (all arguments on one command line).

The opt-in `tests.test_storage_postgres_live` contract test needs a privately
configured `INI_DATABASE_URL`. It uses random synthetic owners, verifies
cross-owner protection and a fresh connection-pool read, then removes only its
own synthetic records. It is skipped when no URL is configured.

Hosted acceptance also requires a full app reboot, restoring a saved chat,
reopening a saved QC answer and checking understood progress. Test another
Google account against the copied chat URL before production rollout.

Existing SQLite records are not automatically migrated. Plan a separate,
owner-preserving migration before switching any deployment whose existing
history must be retained. Do not enable production just by copying staging
Secrets; authorize and verify that rollout separately.
