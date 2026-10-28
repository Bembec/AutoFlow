"""
Gate evidence: no duplicate business effects under failure.

Runs many real shop orders through the order → invoice template in queue
mode (the production setup) while forcing everything that usually causes
duplicates, then counts the actual effects:

  0. a normal order
  1. the same webhook delivered twice (same delivery id)
  2. the store re-sends the order under a new delivery id
  3. the approval button is pressed twice
  4. the mail server fails once, then the retry succeeds
  5. the worker dies while sending; a person confirms the email went out

Expected: exactly one invoice per order, at most one email per order
(exactly one except case 5, where the crash happened before the send),
and one billable event per email actually sent.

CI runs LUPHINA_SOAK_RUNS=60 by default. For the MVP gate run 1,000:
    LUPHINA_SOAK_RUNS=1000 LUPHINA_SOAK_REPORT=../docs/evidence/duplicate-soak.md pytest tests/test_duplicate_soak.py
"""

import base64
import copy
import hashlib
import hmac
import json
import os
import smtplib
import time
from collections import Counter
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select, update

from luphina.engine import queue
from luphina.engine.templates_ecommerce import SAMPLE_SHOPIFY_ORDER
from luphina.storage.db import engine as db_engine
from luphina.storage.db import session_scope, utc_now
from luphina.storage.models import (
    Approval,
    BillableEvent,
    Invoice,
    StepExecution,
    WorkflowExecution,
    Workspace,
)

RUNS = int(os.getenv("LUPHINA_SOAK_RUNS", "60"))
SECRET = "shopify-soak-secret-0123456789"
SCENARIOS = ["normal", "same delivery twice", "redelivered", "double approval", "mail server blip", "crash while sending"]


@pytest.fixture
def mail(monkeypatch):
    """A fake mail server that records every message actually accepted."""
    monkeypatch.setenv("EMAIL_SEND_ENABLED", "true")
    monkeypatch.setenv("LUPHINA_EXECUTION_MODE", "queue")
    sent, failed_once = Counter(), set()
    flaky = set()

    def send_message(message):
        to = message["To"]
        if to in flaky and to not in failed_once:
            failed_once.add(to)
            raise OSError("temporary failure")
        sent[to] += 1

    with patch("luphina.integrations.actions.smtplib") as smtp, patch("luphina.engine.executor.sleep"):
        smtp.SMTPException = smtplib.SMTPException
        smtp.SMTPAuthenticationError = smtplib.SMTPAuthenticationError
        smtp.SMTP_SSL.return_value.__enter__.return_value.send_message.side_effect = send_message
        yield sent, flaky


def work():
    """Run workers until nothing is due."""
    total = 0
    while True:
        with session_scope() as session:
            ran = queue.run_due(session, "soak-worker", limit=50)
        total += ran
        if ran == 0:
            return total


def test_no_duplicate_business_effects(client, signup, mail):
    sent, flaky = mail
    started = time.monotonic()
    headers, workspace_id = signup()
    base = f"/workspaces/{workspace_id}"
    with session_scope() as session:
        session.execute(update(Workspace).where(Workspace.id == workspace_id).values(
            trusted_at=utc_now(), max_executions_per_day=100_000, max_emails_per_day=100_000,
        ))

    client.patch(f"{base}/business", json={"business_name": "Soak Shop Ltd"}, headers=headers)
    client.post(f"{base}/connections", json={
        "provider": "smtp", "name": "mailbox",
        "config": {"host": "smtp.example.com", "username": "shop@example.com", "from_address": "shop@example.com"},
        "secrets": {"password": "app-password-123"},
    }, headers=headers)
    workflow = client.post(f"{base}/workflows/from-template", json={"template": "shopify-order-to-invoice"},
                           headers=headers).json()
    client.post(f"{base}/workflows/{workflow['id']}/publish", headers=headers)
    hook = client.post(f"{base}/workflows/{workflow['id']}/webhook",
                       json={"signature_scheme": "shopify", "secret": SECRET}, headers=headers).json()
    hook_path = "/hooks/" + hook["url"].rsplit("/", 1)[1]

    def deliver(order, delivery_id):
        body = json.dumps(order).encode()
        signature = base64.b64encode(hmac.new(SECRET.encode(), body, hashlib.sha256).digest()).decode()
        response = client.post(hook_path, content=body,
                               headers={"X-Shopify-Hmac-Sha256": signature, "X-Shopify-Webhook-Id": delivery_id})
        assert response.status_code in (200, 202), response.text

    # --- 1. orders arrive, with duplicate and repeated deliveries ---
    orders = []
    for index in range(RUNS):
        scenario = index % len(SCENARIOS)
        email = f"customer{index}@example.com"
        order = copy.deepcopy(SAMPLE_SHOPIFY_ORDER)
        order.update({"id": 5_000_000 + index, "name": f"#{index}", "email": email, "checkout_token": f"chk-{index}"})
        order["customer"] = {**order["customer"], "email": email}
        orders.append((scenario, str(order["id"]), email))
        if scenario == 4:
            flaky.add(email)

        deliver(order, f"delivery-{index}")
        if scenario == 1:
            deliver(order, f"delivery-{index}")
        if scenario == 2:
            deliver(order, f"delivery-{index}-again")
    work()

    # --- 2. a person approves each email (twice for case 3) ---
    with session_scope() as session:
        pending = session.execute(
            select(Approval.id, Approval.execution_id, Approval.customer_email)
            .where(Approval.workspace_id == workspace_id, Approval.status == "pending")
        ).all()
    scenario_of = {email: scenario for scenario, _, email in orders}
    crashed = []
    for approval_id, execution_id, email in pending:
        client.post(f"{base}/approvals/{approval_id}/approve", headers=headers)
        if scenario_of[email] == 3:
            second = client.post(f"{base}/approvals/{approval_id}/approve", headers=headers)
            assert second.status_code >= 400
        if scenario_of[email] == 5:
            crashed.append(execution_id)

    # --- 3. case 5: the worker dies mid-send before the mail server answers ---
    stale = utc_now() - timedelta(hours=1)
    with db_engine.begin() as connection:
        for execution_id in crashed:
            connection.execute(update(WorkflowExecution).where(WorkflowExecution.id == execution_id)
                               .values(status="running", heartbeat_at=stale, claimed_by="dead-worker"))
            connection.execute(update(StepExecution)
                               .where(StepExecution.execution_id == execution_id,
                                      StepExecution.action == "smtp_send_email")
                               .values(status="running", attempts=1))
    work()
    with session_scope() as session:
        queue.recover_stale(session)
    work()

    for execution_id in crashed:
        run = client.get(f"{base}/executions/{execution_id}", headers=headers).json()
        assert run["status"] == "needs_attention"
        # The person checks the customer's inbox, finds the email, and confirms
        done = client.post(f"{base}/executions/{execution_id}/confirm-done", headers=headers)
        assert done.status_code == 200, done.text
    work()

    # --- 4. count the real effects ---
    with session_scope() as session:
        invoices = Counter(session.scalars(select(Invoice.external_ref).where(Invoice.workspace_id == workspace_id)))
        billed_emails = session.scalar(select(func.count(BillableEvent.id)).where(
            BillableEvent.workspace_id == workspace_id, BillableEvent.action == "smtp_send_email"))
        statuses = Counter(session.scalars(
            select(WorkflowExecution.status).where(WorkflowExecution.workspace_id == workspace_id)))
        executions = sum(statuses.values())

    problems = []
    for scenario, ref, email in orders:
        if invoices[ref] != 1:
            problems.append(f"order {ref} ({SCENARIOS[scenario]}): {invoices[ref]} invoices")
        expected_emails = 0 if scenario == 5 else 1
        if sent[email] != expected_emails:
            problems.append(f"order {ref} ({SCENARIOS[scenario]}): {sent[email]} emails, expected {expected_emails}")
    duplicates = len(problems)
    if billed_emails != sum(sent.values()):
        problems.append(f"{billed_emails} billable email events for {sum(sent.values())} emails sent")
    unfinished = {status: n for status, n in statuses.items() if status != "succeeded"}
    if unfinished:
        problems.append(f"runs not finished: {unfinished}")

    report = os.getenv("LUPHINA_SOAK_REPORT")
    if report:
        _write_report(Path(report), orders, executions, sum(invoices.values()), sum(sent.values()),
                      billed_emails, problems, time.monotonic() - started)

    assert not problems, problems[:20]
    assert duplicates == 0


def _write_report(path, orders, executions, invoices, emails, billed, problems, seconds):
    per_scenario = Counter(SCENARIOS[scenario] for scenario, _, _ in orders)
    lines = [
        "# Duplicate-effects soak test",
        "",
        f"Generated by `backend/tests/test_duplicate_soak.py` on {utc_now():%Y-%m-%d %H:%M} UTC "
        f"in {seconds:.0f} s (SQLite, queue mode, fake mail server).",
        "",
        "| Measure | Result |",
        "| --- | --- |",
        f"| Orders | {len(orders):,} |",
        f"| Workflow runs (including duplicates and redeliveries) | {executions:,} |",
        f"| Invoices created | {invoices:,} (one per order expected) |",
        f"| Emails accepted by the mail server | {emails:,} |",
        f"| Billable email events | {billed:,} |",
        f"| Duplicate business effects | **{len(problems)}** |",
        "",
        "Scenarios (orders each):",
        "",
        *[f"- {name}: {count:,}" for name, count in per_scenario.items()],
        "",
        "Result: " + ("**pass**: zero duplicate business effects." if not problems else "**FAIL**"),
    ]
    if problems:
        lines += ["", "Problems:", "", *[f"- {problem}" for problem in problems[:50]]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
