import json
from email.message import EmailMessage
from unittest.mock import patch

import pytest

from luphina import documents, worker
from luphina.integrations import email_inbox
from luphina.storage.db import session_scope


def make_pdf(text):
    """A tiny one-page PDF with a text layer (empty text = a 'scan')."""

    content = f"BT /F1 12 Tf 20 250 Td ({text}) Tj ET".encode() if text else b""
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 300]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(content)).encode() + b">>stream\n" + content + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj".encode() + body + b"endobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer<</Size {len(objects) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF".encode()
    return out


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
INVOICE_TEXT = "Beans Wholesale Invoice SUP-1 Total 144.00 EUR"


def fake_ocr(text="SCANNED: Invoice SUP-9 Total 99.00"):
    return patch("luphina.documents.providers.transcribe", return_value=(text, "fake"))


# --- reading documents -------------------------------------------------------------

def test_detects_type_from_content_not_name():
    assert documents.detect_type(make_pdf("x")) == "application/pdf"
    assert documents.detect_type(PNG) == "image/png"
    assert documents.detect_type(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert documents.detect_type("Grüße".encode()) == "text/plain"
    assert documents.detect_type(b"\x00\xff\xfe\x80\x81binary") == "application/octet-stream"


def test_text_pdf_is_read_without_ai():
    with fake_ocr() as ocr:
        result = documents.extract_text(make_pdf(INVOICE_TEXT), "inv.pdf")

    assert "SUP-1" in result["text"]
    assert (result["method"], result["pages"]) == ("pdf", 1)
    ocr.assert_not_called()


def test_scanned_pdf_and_images_use_ai_ocr():
    with fake_ocr() as ocr:
        scan = documents.extract_text(make_pdf(""), "scan.pdf")
        photo = documents.extract_text(PNG, "photo.png")

    assert scan["method"] == photo["method"] == "ai_ocr:fake"
    assert "SUP-9" in scan["text"]
    assert ocr.call_args_list[1].args[1] == "image/png"


def test_ai_can_be_disallowed_and_bad_files_are_refused():
    with pytest.raises(documents.DocumentError, match="needs AI"):
        documents.extract_text(PNG, allow_ai=False)
    with pytest.raises(documents.DocumentError, match="Unsupported"):
        documents.extract_text(b"\x00\xff\xfe\x80\x81binary")
    with pytest.raises(documents.DocumentError, match="empty"):
        documents.extract_text(b"")
    with pytest.raises(documents.DocumentError, match="larger than"):
        documents.extract_text(b"a" * (documents.MAX_BYTES + 1))


def test_ocr_without_provider_explains_itself():
    with pytest.raises(documents.DocumentError, match="No AI provider"):
        documents.extract_text(PNG)


# --- document uploads ------------------------------------------------------------------

@pytest.fixture
def ws(client, signup):
    headers, workspace_id = signup()
    return client, headers, f"/workspaces/{workspace_id}"


def extract_reply(**data):
    payload = json.dumps({"data": data, "confidence": 0.95})
    return patch("luphina.ai.steps.providers.complete", return_value=(payload, "fake"))


def test_upload_runs_the_supplier_template_in_test_mode(ws):
    client, headers, base = ws
    workflow = client.post(f"{base}/workflows/from-template", json={"template": "supplier-invoice-to-sheet"}, headers=headers).json()

    with extract_reply(supplier="Beans Wholesale", invoice_number="SUP-1", total="144.00", currency="EUR"):
        response = client.post(
            f"{base}/workflows/{workflow['id']}/documents",
            files={"file": ("inv.pdf", make_pdf(INVOICE_TEXT), "application/pdf")},
            data={"mode": "test"},
            headers=headers,
        )

    run = response.json()
    assert response.status_code == 201
    assert run["trigger_payload"]["method"] == "pdf"
    steps = {s["step_id"]: s for s in run["steps"]}
    assert steps["extract"]["output"]["data"]["invoice_number"] == "SUP-1"
    assert steps["row"]["output"]["dry_run"] is True


def test_live_uploads_need_a_document_trigger(ws):
    client, headers, base = ws
    manual = client.post(f"{base}/workflows", json={"name": "M", "definition": {
        "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "{{trigger.text}}"}}],
    }}, headers=headers).json()
    client.post(f"{base}/workflows/{manual['id']}/publish", headers=headers)

    refused = client.post(f"{base}/workflows/{manual['id']}/documents",
                          files={"file": ("a.txt", b"hello", "text/plain")}, headers=headers)
    assert refused.status_code == 409

    doc = client.post(f"{base}/workflows", json={"name": "D", "definition": {
        "trigger": {"type": "document"},
        "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "{{trigger.text}}"}}],
    }}, headers=headers).json()
    client.post(f"{base}/workflows/{doc['id']}/publish", headers=headers)

    accepted = client.post(f"{base}/workflows/{doc['id']}/documents",
                           files={"file": ("a.txt", b"hello from a file", "text/plain")}, headers=headers)
    assert accepted.status_code == 201
    assert accepted.json()["steps"][0]["input"]["message"] == "hello from a file"


def test_unreadable_upload_is_rejected(ws):
    client, headers, base = ws
    workflow = client.post(f"{base}/workflows/from-template", json={"template": "supplier-invoice-to-sheet"}, headers=headers).json()

    response = client.post(f"{base}/workflows/{workflow['id']}/documents",
                           files={"file": ("x.bin", b"\x00\xff\xfe\x80binary", "application/pdf")},
                           data={"mode": "test"}, headers=headers)

    assert response.status_code == 422


# --- email -----------------------------------------------------------------------------

def make_email(subject="Invoice SUP-1", message_id="<abc@beans.example>", html=False, attach=True):
    message = EmailMessage()
    message["From"] = "Beans Wholesale <billing@beans.example>"
    message["To"] = "invoices@shop.example"
    message["Subject"] = subject
    if message_id:
        message["Message-ID"] = message_id
    if html:
        message.set_content("<p>Hello,<br>see <b>invoice</b> &amp; terms</p>", subtype="html")
    else:
        message.set_content("Hello, please find our invoice attached.")
    if attach:
        message.add_attachment(make_pdf(INVOICE_TEXT), maintype="application", subtype="pdf", filename="SUP-1.pdf")
    return message.as_bytes()


def test_parse_email_with_pdf_attachment():
    payload = email_inbox.parse_message(make_email())

    assert payload["subject"] == "Invoice SUP-1"
    assert payload["message_id"] == "<abc@beans.example>"
    assert payload["text"] == "Hello, please find our invoice attached."
    assert payload["attachments"][0]["filename"] == "SUP-1.pdf"
    assert "SUP-1" in payload["attachments_text"]


def test_parse_html_only_email_and_missing_message_id():
    raw = make_email(html=True, message_id=None, attach=False)
    payload = email_inbox.parse_message(raw)

    assert "see invoice & terms" in " ".join(payload["text"].split())
    assert payload["message_id"].startswith("sha256:")
    assert email_inbox.parse_message(raw)["message_id"] == payload["message_id"]


class FakeIMAP:
    """Just enough of imaplib.IMAP4_SSL for the poller."""

    def __init__(self, messages):
        self.messages = messages  # uid -> raw bytes
        self.seen = set()

    def select(self, folder):
        return ("OK", [b"1"]) if folder == "INBOX" else ("NO", [b""])

    def uid(self, command, *args):
        if command == "SEARCH":
            unseen = [uid for uid in self.messages if uid not in self.seen]
            return "OK", [b" ".join(unseen)]
        if command == "FETCH":
            return "OK", [(b"1 (BODY[] {n})", self.messages[args[0]]), b")"]
        if command == "STORE":
            self.seen.add(args[0])
            return "OK", []
        raise AssertionError(command)

    def logout(self):
        pass


def email_workflow(ws):
    client, headers, base = ws
    client.post(f"{base}/connections", json={
        "provider": "imap", "name": "invoices-inbox",
        "config": {"host": "imap.example.com", "username": "invoices@shop.example"},
        "secrets": {"password": "app-password-1234"},
    }, headers=headers)
    workflow = client.post(f"{base}/workflows", json={"name": "Mail", "definition": {
        "trigger": {"type": "email", "connection": "invoices-inbox"},
        "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "{{trigger.subject}}"}}],
    }}, headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    return workflow


def test_email_trigger_needs_a_connection(ws):
    client, headers, base = ws

    response = client.post(f"{base}/workflows", json={"name": "Mail", "definition": {
        "trigger": {"type": "email"},
        "steps": [{"id": "log", "action": "log_activity", "inputs": {"message": "x"}}],
    }}, headers=headers)

    assert response.status_code == 422


def test_inbox_poll_starts_one_run_per_message(ws):
    client, headers, base = ws
    email_workflow(ws)
    imap = FakeIMAP({b"1": make_email("First", "<1@x>"), b"2": make_email("Second", "<2@x>")})

    with patch("luphina.integrations.email_inbox._connect", return_value=imap):
        with session_scope() as session:
            first = worker.run_email_triggers(session)
        with session_scope() as session:
            again = worker.run_email_triggers(session)

    assert (first, again) == (2, 0)
    assert imap.seen == {b"1", b"2"}
    subjects = {e["trigger_payload"]["subject"] for e in client.get(f"{base}/executions", headers=headers).json()}
    assert subjects == {"First", "Second"}


def test_a_message_is_never_processed_twice(ws):
    client, headers, base = ws
    email_workflow(ws)
    imap = FakeIMAP({b"1": make_email("Only once", "<once@x>")})
    imap.uid = _store_fails(imap.uid)  # marking as read keeps failing

    with patch("luphina.integrations.email_inbox._connect", return_value=imap):
        for _ in range(3):
            with session_scope() as session:
                worker.run_email_triggers(session)

    assert len(client.get(f"{base}/executions", headers=headers).json()) == 1


def _store_fails(original):
    def uid(command, *args):
        if command == "STORE":
            return "NO", []
        return original(command, *args)
    return uid


def test_missing_mail_connection_skips_quietly(ws):
    client, headers, base = ws
    workflow = email_workflow(ws)
    connection = client.get(f"{base}/connections", headers=headers).json()[0]
    client.delete(f"{base}/connections/{connection['id']}", headers=headers)

    with patch("luphina.integrations.email_inbox._connect") as connect:
        with session_scope() as session:
            assert worker.run_email_triggers(session) == 0

    connect.assert_not_called()
    assert workflow["id"]
