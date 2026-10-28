from pathlib import Path
from unittest.mock import patch

from luphina import help_assistant
from luphina.ai import providers

DOCS = Path(__file__).resolve().parents[2] / "docs" / "help"


def test_packaged_help_matches_docs():
    # Run `python scripts/sync_help.py` after editing docs/help
    for path in DOCS.glob("*.md"):
        assert (help_assistant.HELP_DIR / path.name).read_text(encoding="utf-8") == path.read_text(encoding="utf-8"), path.name


def test_search_finds_the_right_section():
    best = help_assistant.search("how do I void an invoice")[0]
    assert "void" in best["section"].lower()


def test_ask_answers_from_help_and_does_not_use_the_customers_ai_budget(client, signup):
    headers, workspace_id = signup()
    with patch("luphina.help_assistant.providers.complete", return_value=("Press Void on Invoices.", "fake")) as ai:
        reply = client.post(f"/workspaces/{workspace_id}/help/ask", json={"question": "How do I void an invoice?"},
                            headers=headers).json()
    assert reply["ai"] and reply["answer"] == "Press Void on Invoices." and reply["sources"]
    assert "Help sections" in ai.call_args.args[1]
    usage = client.get(f"/workspaces/{workspace_id}/dashboard", headers=headers).json()["usage_today"]
    assert usage["ai_calls"] == 0

    with patch("luphina.help_assistant.providers.complete", side_effect=providers.AIUnavailable("none")):
        fallback = client.post(f"/workspaces/{workspace_id}/help/ask", json={"question": "AI budget"},
                               headers=headers).json()
    assert fallback["ai"] is False and fallback["excerpts"]
