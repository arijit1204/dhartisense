# Accounts and fields (Firebase setup)

Accounts, email verification, password reset and field storage use Firebase, on its free Spark plan (no card needed). Firebase Authentication stores the passwords and sends the verification and reset emails. Fields are kept in Firestore under `users/{uid}/fields/{id}`, written only by this server (`app/fbstore.py`). A signed-in browser holds an HttpOnly session cookie (14 days). All API routes except health, config and sign-in need that session, so the Groq and weather quotas cannot be used anonymously.

## One-time setup (about 10 minutes)

1. Go to <https://console.firebase.google.com>, **Add project** (turn Google Analytics off).
2. **Build > Authentication > Get started > Email/Password > Enable** (leave "Email link" off).
3. **Build > Firestore Database > Create database**, choose **Production mode** and a region near your farmers (for India, `asia-south1` Mumbai). Then open **Rules**, paste the contents of `deploy/firestore.rules`, and Publish.
4. **Project settings (gear) > General > Your apps > Web (`</>`)**: register an app, copy `apiKey` and `projectId`.
5. **Project settings > Service accounts > Generate new private key**: save the JSON file somewhere private.
6. **Authentication > Templates**: edit the "Email address verification" and "Password reset" emails (set the sender name to Dhartisense, add your language). The default sender is Firebase's, which works with no setup. A custom sender domain is optional later.
7. **Authentication > Settings > Authorized domains**: add your real domain when you deploy (`localhost` is already there).
8. In `.env` set `FIREBASE_PROJECT_ID`, `FIREBASE_API_KEY` and `FIREBASE_SERVICE_ACCOUNT_FILE` (the path to the JSON from step 5). Then run `venv/Scripts/python.exe scripts/check_firebase.py`: it should print Authentication OK and Firestore OK. Install the dependency with `venv/Scripts/python.exe -m pip install -r requirements.txt`.

## Before going public

- Serve over HTTPS and set `DHARTISENSE_COOKIE_SECURE=1`.
- Free-plan limits (Firestore: 50,000 reads and 20,000 writes a day; Authentication: very high for email/password) are plenty for a pilot; watch the Usage tab and set a budget alert in Google Cloud.
- Registration checks that the email's domain can receive mail (a DNS lookup of the domain only, through Google's public DNS-over-HTTPS), then Firebase's verification email is the proof the address works. The app stays locked until the link is opened.
- Signing out revokes the account's refresh tokens; another device's session cookie ends at its next renewal. The per-request revocation check is skipped for speed.
- Back up Firestore on a schedule (Console > Firestore > Disaster recovery) once real farmers use it.
- 
For development without cloud setup, run the Firebase emulator for Authentication (`npx firebase-tools emulators:start --only auth`), set `FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099` and `DHARTISENSE_FIRESTORE=memory` (fields kept in memory), plus any project id and API key.

Calendar: the Water page and Overview offer "Add to Google Calendar" links and an `.ics` file with a reminder the evening before and on the morning of each irrigation. This is not an automatic sync.
