// Firebase Authentication through its official REST API (https://firebase.google.com/docs/reference/rest/auth).
// Firebase stores the passwords and sends the verification and reset emails. Nothing is stored in the browser: the server's session cookie keeps the
// farmer signed in, and the Firebase sign-in state below lives in memory only (so strict tracking protection cannot break sign-in).
(() => {
  let key = "";
  let host = "https://identitytoolkit.googleapis.com";
  let tokenHost = "https://securetoken.googleapis.com";
  let me = null;

  const CODES = {
    EMAIL_EXISTS: "auth/email-already-in-use", INVALID_EMAIL: "auth/invalid-email", WEAK_PASSWORD: "auth/weak-password", INVALID_PASSWORD: "auth/invalid-credential",
    EMAIL_NOT_FOUND: "auth/invalid-credential", INVALID_LOGIN_CREDENTIALS: "auth/invalid-credential", TOO_MANY_ATTEMPTS_TRY_LATER: "auth/too-many-requests",
    USER_DISABLED: "auth/user-disabled", OPERATION_NOT_ALLOWED: "auth/operation-not-allowed", TOKEN_EXPIRED: "auth/user-token-expired",
  };

  async function call(url, body, form) {
    let response;
    try {
      response = await fetch(`${url}?key=${encodeURIComponent(key)}`, form
        ? { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams(body) }
        : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    } catch {
      throw { code: "auth/network-request-failed" };
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = String(data.error?.message || "");
      const code = Object.keys(CODES).find((k) => message.startsWith(k));
      throw { code: code ? CODES[code] : "auth/unknown", message };
    }
    return data;
  }

  const account = (path, body) => call(`${host}/v1/accounts:${path}`, body);

  function adopt(data) {
    me = { ...(me || {}), email: data.email || me?.email, idToken: data.idToken || data.id_token || me?.idToken, refreshToken: data.refreshToken || data.refresh_token || me?.refreshToken }; // a reply without new tokens keeps the current ones
    return me;
  }

  async function reload(user) {
    const fresh = await call(`${tokenHost}/v1/token`, { grant_type: "refresh_token", refresh_token: user.refreshToken }, true); // new token, so it carries the latest email_verified
    adopt(fresh);
    const info = (await account("lookup", { idToken: me.idToken })).users?.[0] || {};
    me.emailVerified = Boolean(info.emailVerified);
    me.displayName = info.displayName || "";
    return me;
  }

  window.farmAuth = {
    init(config) {
      key = config.apiKey;
      if (config.authEmulator) {
        host = `${config.authEmulator}/identitytoolkit.googleapis.com`;
        tokenHost = `${config.authEmulator}/securetoken.googleapis.com`;
      }
    },
    current: () => me,
    async register(email, password, name) {
      me = null;
      adopt(await account("signUp", { email, password, returnSecureToken: true }));
      adopt(await account("update", { idToken: me.idToken, displayName: name, returnSecureToken: true }));
      await account("sendOobCode", { requestType: "VERIFY_EMAIL", idToken: me.idToken });
      me.emailVerified = false;
      return me;
    },
    async login(email, password) {
      me = null;
      adopt(await account("signInWithPassword", { email, password, returnSecureToken: true }));
      return reload(me);
    },
    reload,
    idToken: async (user) => (await reload(user)).idToken,
    async sendVerification(user) {
      await account("sendOobCode", { requestType: "VERIFY_EMAIL", idToken: (await reload(user)).idToken });
    },
    sendReset: (email) => account("sendOobCode", { requestType: "PASSWORD_RESET", email }),
    signOut() {
      me = null;
      return Promise.resolve();
    },
  };
})();
