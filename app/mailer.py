"""Email address check used before sign-up.

Firebase Authentication sends the verification and password-reset emails, so this app sends no email itself. This only catches typos and fake
domains early: the address must be well formed and its domain must be able to receive mail.
"""

import json
import re
import time
import urllib.parse
import urllib.request

EMAIL = re.compile(r"^(?!\.)(?!.*\.\.)[A-Za-z0-9._%+-]{1,64}(?<!\.)@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,24}$")
_mx_cache: dict = {}


def domain_can_receive_mail(email: str) -> bool:
    """True when the domain publishes a mail server (an MX record, or an address record as a fallback).
    Asks Google's public DNS-over-HTTPS service about the domain only, never the full address. If the lookup itself fails the address is accepted:
    the verification email is the real proof."""
    domain = email.rsplit("@", 1)[-1].lower()
    cached = _mx_cache.get(domain)
    if cached and time.time() - cached[0] < 6 * 3600:
        return cached[1]
    try:
        for record in ("MX", "A"):
            url = "https://dns.google/resolve?" + urllib.parse.urlencode({"name": domain, "type": record})
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/dns-json"}), timeout=6) as response:
                answer = json.loads(response.read()).get("Answer") or []
            if any(a.get("type") in (15, 1) for a in answer):
                _mx_cache[domain] = (time.time(), True)
                return True
        _mx_cache[domain] = (time.time(), False)
        return False
    except (OSError, ValueError):
        return True


if __name__ == "__main__":
    assert all(EMAIL.match(e) for e in ("a@gmail.com", "first.last+tag@sub.example.co.in"))
    assert not any(EMAIL.match(e) for e in ("a@gmial..com", "a..b@x.com", ".a@x.com", "a@x", "a b@x.com", "a@-x.com", ""))
    assert domain_can_receive_mail("someone@gmail.com") and not domain_can_receive_mail("a@zzzz-not-real-domain-12345.com")
    print("mailer self-check passed")
