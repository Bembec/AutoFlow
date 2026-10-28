"""
Outbound message checks: stop Luphina being used to send phishing or spam.

Runs on every email step before it is approved or sent. Two levels:

- "block": the message looks like credential phishing (asks for a
  password or security code and links somewhere). The step fails and the
  event is logged for staff; approving it is not possible.
- "warn": signs of spam or a risky link (link shorteners, raw IP
  addresses, many links, many recipients). The approver sees why.

The rules are deliberately simple and explainable; they catch abuse of
the platform, not every bad email.
"""

import re
from urllib.parse import urlparse

URL = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "rebrand.ly", "cutt.ly", "shorturl.at",
}
# Asking the reader for secrets no honest business requests by email
SECRET_REQUESTS = re.compile(
    r"\b(verify|confirm|update|validate|re-?enter|provide|send us|enter)\b[^.\n]{0,60}"
    r"\b(password|passcode|login details|credentials|cvv|security code|seed phrase|one-time code)\b",
    re.IGNORECASE,
)
# Payment details: legitimate in a failed-payment email, so only a warning
PAYMENT_REQUESTS = re.compile(
    r"\b(verify|confirm|update|validate|re-?enter|provide|send us)\b[^.\n]{0,60}"
    r"\b(card number|card details|bank details|bank account)\b",
    re.IGNORECASE,
)
URGENT_THREATS = re.compile(
    r"\b(account (will be )?(suspended|locked|closed|disabled)|within 24 hours|immediately or)\b", re.IGNORECASE
)
MAX_LINKS = 10
MAX_RECIPIENTS = 20


def _recipients(value):
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [part for part in re.split(r"[,;]\s*", str(value or "")) if part.strip()]


def check_email(inputs):
    """Findings for one outgoing email: [{"level": "block"|"warn", "reason": str}]."""

    subject = str(inputs.get("subject") or "")
    body = str(inputs.get("body") or "")
    text = f"{subject}\n{body}"
    links = URL.findall(text)
    findings = []

    def add(level, reason):
        findings.append({"level": level, "reason": reason})

    if SECRET_REQUESTS.search(text) and links:
        add("block", "The message asks the reader for a password or security code and contains a link. "
                     "This is how phishing works, so it can't be sent.")
    elif SECRET_REQUESTS.search(text):
        add("warn", "The message asks the reader for a password or security code.")
    if PAYMENT_REQUESTS.search(text):
        add("warn", "The message asks the reader to send or update card or bank details. "
                    "Make sure it links only to your own shop's checkout.")

    if URGENT_THREATS.search(text):
        add("warn", "The message threatens to close or lock an account, a common spam and phishing pattern.")

    hosts = {urlparse(link).hostname or "" for link in links}
    if hosts & SHORTENERS:
        add("warn", "The message uses a link shortener, which hides where the link goes.")
    if any(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host) for host in hosts):
        add("warn", "A link points to a raw IP address instead of a website name.")
    if len(links) > MAX_LINKS:
        add("warn", f"The message contains {len(links)} links.")

    recipients = _recipients(inputs.get("to")) + _recipients(inputs.get("cc")) + _recipients(inputs.get("bcc"))
    if len(recipients) > MAX_RECIPIENTS:
        add("warn", f"The message goes to {len(recipients)} recipients at once.")

    return findings


def blocking(findings):
    return [finding for finding in findings if finding["level"] == "block"]
