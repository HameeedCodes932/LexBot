import json
from unittest.mock import patch

from agent_tools import (
    send_email, draft_email, create_file, list_directory,
    web_search, create_reminder, TOOL_REGISTRY,
)


class TestToolRegistry:
    def test_has_all_tools(self):
        names = [t["name"] for t in TOOL_REGISTRY]
        assert "send_email" in names
        assert "draft_email" in names
        assert "open_file" in names
        assert "create_file" in names
        assert "list_directory" in names
        assert "web_search" in names
        assert "create_reminder" in names
        assert "summarize_document" in names

    def test_each_tool_has_required_keys(self):
        for tool in TOOL_REGISTRY:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert isinstance(tool["parameters"], dict)


class TestDraftEmail:
    def test_returns_draft_with_status(self):
        result = draft_email("client@test.com", "Hello", "Body text")
        assert result["success"] is True
        assert result["result"]["to"] == "client@test.com"
        assert result["result"]["subject"] == "Hello"
        assert "drafted" in result["result"]["status"].lower()


class TestSendEmail:
    @patch("agent_tools.config.SMTP_EMAIL", "")
    def test_fails_without_credentials(self):
        result = send_email("t@t.com", "S", "B")
        assert result["success"] is False
        assert "credentials" in result["error"].lower()

    @patch("agent_tools.config.SMTP_EMAIL", "test@test.com")
    @patch("agent_tools.config.SMTP_PASSWORD", "pass")
    def test_fails_on_smtp_error(self):
        result = send_email("t@t.com", "S", "B")
        assert result["success"] is False


class TestCreateFile:
    def test_creates_txt_file(self):
        result = create_file("test.txt", "hello world", "txt")
        assert result["success"] is True

    def test_fails_on_unsupported_type(self):
        result = create_file("test.bin", "data", "bin")
        assert result["success"] is False
        assert "unsupported" in result["error"].lower()


class TestWebSearch:
    @patch("duckduckgo_search.DDGS")
    def test_search_returns_formatted_results(self, mock_ddgs_class):
        mock_instance = mock_ddgs_class.return_value.__enter__.return_value
        mock_instance.text.return_value = [
            {"title": "Result 1", "body": "Snippet 1", "href": "https://example.com/1"},
            {"title": "Result 2", "body": "Snippet 2", "href": "https://example.com/2"},
        ]

        result = web_search("test query", max_results=2)
        assert result["success"] is True
        assert len(result["result"]["results"]) == 2
        assert result["result"]["results"][0]["title"] == "Result 1"

    @patch("duckduckgo_search.DDGS")
    def test_search_handles_empty_results(self, mock_ddgs_class):
        mock_instance = mock_ddgs_class.return_value.__enter__.return_value
        mock_instance.text.return_value = []

        result = web_search("nonexistent query")
        assert result["success"] is True
        assert result["result"]["results"] == []


class TestCreateReminder:
    def test_creates_ics_file(self):
        result = create_reminder("Meeting", "2026-07-01 10:00", "Team sync")
        assert result["success"] is True
        assert "Meeting" in result["result"]

    def test_handles_invalid_date(self):
        result = create_reminder("Test", "not-a-date")
        assert result["success"] is False


class TestListDirectory:
    def test_lists_files(self):
        result = list_directory()
        assert result["success"] is True
        assert "file_count" in result["result"]
        assert "files" in result["result"]
