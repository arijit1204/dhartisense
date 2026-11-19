# Security policy

## Reporting a vulnerability

Please do **not** open a public issue for a security problem. Use GitHub's private reporting instead: open the repository's **Security** tab and choose **Report a vulnerability** (or go to `../../security/advisories/new`). Include what you found, the steps to reproduce it and the impact. You will get a reply as soon as the maintainer can; this is a volunteer project, so please allow some days.

## What to protect if you run your own copy

- Never commit `.env` or any Firebase service-account key. Keep the key file outside the project folder. `.gitignore` blocks the common patterns, but check `git status` before every push.
- If a key is ever exposed (committed, pasted in a chat, shared in a screenshot), **revoke it and create a new one**; deleting the file or the commit is not enough. Groq keys: console.groq.com. Firebase service accounts: Google Cloud console > IAM & Admin > Service accounts > Keys.
- Serve the site over HTTPS only and set `DHARTISENSE_COOKIE_SECURE=1`.
- Restrict your Firebase web API key to your site's address in the Google Cloud console and keep `deploy/firestore.rules` published so browsers cannot read the database directly.
