import unittest
from streamlit.testing.v1 import AppTest


class GoogleSigninGateTests(unittest.TestCase):
    def test_missing_configuration_blocks_conversation_content(self):
        app = AppTest.from_string('''
import streamlit as st
from unittest.mock import patch
from streamlit_app.google_signin import require_google_account
st.query_params["visitor"] = "copied-visitor-value"
with patch.object(type(st.secrets), "to_dict", return_value={}):
    require_google_account()
st.write("PRIVATE CONTENT MUST NEVER RENDER")
''').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.button[0].label, "Continue with Google")
        self.assertTrue(app.button[0].disabled)
        self.assertNotIn("visitor", app.query_params)
        self.assertFalse(any("PRIVATE CONTENT" in element.value for element in app.markdown))

    def test_verified_account_not_visitor_url_controls_owner(self):
        app = AppTest.from_string('''
import streamlit as st
import time
from unittest.mock import patch
from streamlit_app.google_signin import require_google_account
config = {"auth": {"redirect_uri": "http://localhost:8501/oauth2callback", "cookie_secret": "a"*64,
 "google": {"client_id": "client", "client_secret": "secret", "server_metadata_url":
 "https://accounts.google.com/.well-known/openid-configuration"}}}
claims = {"is_logged_in": True, "iss": "https://accounts.google.com", "aud": "client",
 "sub": "account-a", "email_verified": True, "exp": time.time()+3600}
st.query_params["visitor"] = "someone-elses-url"
with patch.object(type(st.secrets), "to_dict", return_value=config), patch("streamlit_app.google_signin.find_spec", return_value=object()), patch("streamlit_app.google_signin.st.user", claims):
    owner = require_google_account()
st.write(owner)
''').run()
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn("visitor", app.query_params)
        self.assertTrue(app.session_state["visitor_id"].startswith("google-"))
        self.assertNotEqual(app.session_state["visitor_id"], "someone-elses-url")


if __name__ == "__main__":
    unittest.main()
