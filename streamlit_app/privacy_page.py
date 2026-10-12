"""Public privacy notice; renders without account, storage, or model access."""
from pathlib import Path
import streamlit as st

PRIVACY_TEXT = """
Last updated: October 12, 2026

InI.ai (Interrogate n Illustrate) is an alpha-stage educational question engine
operated by Sudipto Bhadra. This notice covers the InI app and its sign-in test
deployment. Privacy questions and data requests can be sent to
[sudiptoini@gmail.com](mailto:sudiptoini@gmail.com).

### What InI receives

- **Google sign-in, where enabled:** Google supplies a unique account identifier,
  verified email address and basic profile information such as your name and
  profile image. InI uses the identity to sign you in and associate your learning
  records with your account. The database ownership key is derived from Google's
  account identifier, not a public chat URL. InI does not receive your Google
  password.
- **Information you enter:** questions, conversation context, generated answers,
  chat titles, subject maps, chapter questions, saved answers, learning progress
  and record timestamps. Anything personal that you include in a prompt becomes
  part of the submitted content.
- **Legacy visitor mode:** deployments that still allow anonymous access use a
  generated visitor identifier in the URL. This is not Google sign-in and does
  not provide the same identity protection. Avoid sharing legacy visitor links.
- **Technical information:** our hosting and service providers may process IP
  addresses, browser/device information, authentication cookies, request metadata
  and operational or security logs. App diagnostics can include response content.

### What InI does not request from Google

InI uses basic identity scopes for sign-in: openid, email and profile. It does
not request permission to read your Gmail messages, Google Drive files,
contacts, calendar or other Google account content. Signing in does not grant
InI access to those services.

### Why information is processed

Information is used to authenticate you, generate educational responses, save
and restore conversations and learning progress, operate the app, investigate
errors or abuse and respond to support or deletion requests. Do not submit
passwords, payment-card details, government identifiers, confidential documents
or sensitive medical or other personal information.

### Services involved in processing

- **Google:** authenticates your account when you choose Google sign-in.
- **OpenAI:** receives your prompt, relevant context and instructions needed to
  generate answers. InI is not an offline or zero-retention AI service. OpenAI's
  processing and retention depend on the API endpoint and account settings;
  [OpenAI's API data-controls documentation](https://developers.openai.com/api/docs/guides/your-data)
  explains these separately.
- **Streamlit Community Cloud and, where configured, Render:** host the app or
  its answer service and process the requests and operational data needed to
  provide them.
- **Neon, where configured:** stores conversations and curriculum state in
  PostgreSQL. Some alpha deployments still use server-local SQLite storage;
  those records may be lost when the server restarts or is redeployed.
- **Public knowledge sources:** topic or search terms derived from a request may
  be sent to reference-service APIs to retrieve educational material. A topic can
  itself contain personal information if you put it in your question.

These providers have their own privacy and retention practices. Processing may
take place outside your country, including in the United States. See
[Google's privacy policy](https://policies.google.com/privacy),
[Streamlit's privacy notice](https://streamlit.io/privacy-policy),
[Render's privacy policy](https://render.com/privacy) and
[Neon's privacy policy](https://neon.com/privacy-policy).

### Storage, access and security

On account-enabled deployments, application ownership checks restrict access
to the signed-in owner's conversations and curricula. HTTPS protects hosted
connections; the Neon integration uses certificate-verified TLS. Credentials
are kept in private configuration, not public source code.

This is not end-to-end encryption. The operator and authorized service-provider
personnel may have access to data for operations, troubleshooting, security or
handling data requests. No system can guarantee absolute security. InI remains
in alpha; these safeguards are not a claim of a completed independent security
audit or certification.

### Retention and deletion

InI currently has no automatic conversation-expiry schedule. Saved records can
remain until you delete them or request their removal. Where available, the
chat menu lets you delete a conversation record. To request removal of all
associated curriculum or account records, contact
[sudiptoini@gmail.com](mailto:sudiptoini@gmail.com) from the email used to sign in.
We may verify ownership before acting; do not send your password.

Deleting a chat from InI does not necessarily immediately erase separate
provider logs, backups or records held by OpenAI or other services. Those are
subject to their own retention rules. Signing out or revoking Google access
does not by itself delete previously saved InI records.

### Your choices

You can choose not to sign in or submit content, sign out, delete conversations
where the app offers that control, and contact us to request access, correction
or removal of your associated records. You can also remove InI's connection in
your Google Account settings. Blocking essential cookies may prevent sign-in.
Depending on where you live, additional privacy rights may apply.

### Changes to this notice

The app and its privacy practices may change as the alpha develops. This page
will be updated with the date above when the notice changes. Contact
[sudiptoini@gmail.com](mailto:sudiptoini@gmail.com) with questions.
""".strip()


def render_privacy_page():
    with st.container(width=850):
        st.image(str(Path(__file__).with_name("ini_buta_icon_white.png")), width=56)
        st.title("InI.ai Privacy Policy")
        st.markdown(PRIVACY_TEXT)
        st.markdown("[Back to InI](?page=home)")


def show_public_privacy_page() -> bool:
    if st.query_params.get("page") != "privacy":
        return False
    render_privacy_page()
    return True
