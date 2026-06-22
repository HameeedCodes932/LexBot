import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import config


# ── Sandbox helpers ────────────────────────────────────────────────────────────

def _ensure_sandbox():
    """Create the agent sandbox directory if it doesn't exist."""
    os.makedirs(config.AGENT_FILES_DIR, exist_ok=True)


def _safe_path(file_path: str) -> str:
    """
    Resolve a file path inside the agent sandbox directory.
    Prevents path traversal attacks (e.g., ../../etc/passwd).
    """
    _ensure_sandbox()
    # If the user gives an absolute path, take only the basename
    if os.path.isabs(file_path):
        file_path = os.path.basename(file_path)
    resolved = os.path.normpath(os.path.join(config.AGENT_FILES_DIR, file_path))
    if not resolved.startswith(os.path.normpath(config.AGENT_FILES_DIR)):
        raise ValueError(f"Path escapes sandbox: {file_path}")
    return resolved


# ── Tool Functions ─────────────────────────────────────────────────────────────

def send_email(to: str, subject: str, body: str, cc: str = "") -> dict:
    """Send an email via Gmail SMTP."""
    if not config.SMTP_EMAIL or not config.SMTP_PASSWORD:
        return {"success": False, "error": "SMTP credentials not configured. Set SMTP_EMAIL and SMTP_PASSWORD in .env."}
    try:
        msg = MIMEMultipart()
        msg["From"] = config.SMTP_EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        msg.attach(MIMEText(body, "plain"))
        recipients = [to] + ([cc] if cc else [])
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_EMAIL, recipients, msg.as_string())
        return {"success": True, "result": f"Email sent to {to} with subject '{subject}'."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def draft_email(to: str, subject: str, body: str) -> dict:
    """Draft an email without sending it."""
    return {
        "success": True,
        "result": {
            "to": to,
            "subject": subject,
            "body": body,
            "status": "drafted — not sent. Confirm to send."
        }
    }


def open_file(file_path: str) -> dict:
    """Read a file from the agent sandbox directory."""
    try:
        resolved = _safe_path(file_path)
        if not os.path.exists(resolved):
            return {"success": False, "error": f"File not found: {os.path.basename(file_path)}"}
        ext = resolved.rsplit(".", 1)[-1].lower()
        if ext == "txt":
            with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        elif ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(resolved)
            content = "\n".join(
                page.extract_text() for page in reader.pages if page.extract_text()
            )
        elif ext == "docx":
            from docx import Document
            doc = Document(resolved)
            content = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        else:
            return {"success": False, "error": f"Unsupported file type: {ext}"}
        return {
            "success": True,
            "result": {
                "file_path": os.path.basename(resolved),
                "content": content[:5000],
                "total_characters": len(content)
            }
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_file(file_path: str, content: str, file_type: str = "txt") -> dict:
    """Create a new file in the agent sandbox directory."""
    try:
        resolved = _safe_path(file_path)
        folder = os.path.dirname(resolved)
        if folder:
            os.makedirs(folder, exist_ok=True)
        if file_type == "txt":
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(content)
        elif file_type == "docx":
            from docx import Document
            doc = Document()
            for line in content.split("\n"):
                if line.strip():
                    doc.add_paragraph(line)
            doc.save(resolved)
        else:
            return {"success": False, "error": f"Unsupported file type: {file_type}"}
        return {"success": True, "result": f"File created: {os.path.basename(resolved)}"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_directory(directory_path: str = "", extension_filter: str = "") -> dict:
    """List files in the agent sandbox directory."""
    try:
        _ensure_sandbox()
        target = config.AGENT_FILES_DIR
        if directory_path and directory_path.strip() and directory_path != ".":
            # Only allow subdirectories within sandbox
            target = _safe_path(directory_path)
        if not os.path.isdir(target):
            return {"success": False, "error": f"Directory not found."}
        files = []
        for fname in os.listdir(target):
            full_path = os.path.join(target, fname)
            if os.path.isfile(full_path):
                if extension_filter and not fname.endswith(extension_filter):
                    continue
                files.append({
                    "name": fname,
                    "size_kb": round(os.path.getsize(full_path) / 1024, 1),
                    "extension": fname.rsplit(".", 1)[-1] if "." in fname else ""
                })
        return {
            "success": True,
            "result": {
                "directory": "agent_files",
                "file_count": len(files),
                "files": files
            }
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _ddg_search(query: str, max_results: int) -> list:
    from duckduckgo_search import DDGS
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    with DDGS(headers={"User-Agent": ua}) as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        if results:
            return results
        results = list(ddgs._text_bing(query, max_results=max_results))
        return results


def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web using DuckDuckGo (falls back to Bing backend)."""
    try:
        results = _ddg_search(query, max_results)
        formatted = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", "")[:300],
                "url": r.get("href", "")
            }
            for r in results
        ]
        return {"success": True, "result": {"query": query, "results": formatted}}
    except Exception as e:
        return {"success": False, "error": f"Web search failed: {str(e)}"}


def create_reminder(title: str, date: str, description: str = "", output_path: str = "reminder.ics") -> dict:
    """Create a calendar reminder as an .ics file in the agent sandbox."""
    try:
        from ics import Calendar, Event
        from datetime import datetime
        resolved = _safe_path(output_path)
        c = Calendar()
        e = Event()
        e.name = title
        e.description = description
        if " " in date:
            e.begin = datetime.strptime(date, "%Y-%m-%d %H:%M")
        else:
            e.begin = datetime.strptime(date, "%Y-%m-%d")
        c.events.add(e)
        with open(resolved, "w") as f:
            f.write(str(c))
        return {
            "success": True,
            "result": f"Reminder '{title}' set for {date}. File saved as {os.path.basename(resolved)}."
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def summarize_document(document_name: str, user_id: int) -> dict:
    """Summarize an uploaded LexBot document from pgvector."""
    try:
        from ingestion import ingestion_service
        from database import async_session_factory
        async with async_session_factory() as session:
            chunks = await ingestion_service.get_chunks_by_source(session, user_id, document_name)
            all_text = "\n\n".join(c.content for c in chunks) if chunks else ""
            if not all_text.strip():
                return {"success": False, "error": f"No content found for '{document_name}'. Make sure the file is uploaded first."}
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage
        llm = ChatGroq(api_key=config.GROQ_API_KEY, model=config.GROQ_MEMORY_MODEL, temperature=0)
        prompt = f"""Summarize this legal document in 5-7 bullet points.
Focus on: parties involved, key obligations, important dates, and any unusual terms.

DOCUMENT:
{all_text[:4000]}

Summary:"""
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"success": True, "result": response.content.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Tool Registry ─────────────────────────────────────────────────────────────

TOOL_REGISTRY = [
    {
        "name": "send_email",
        "description": "Send an email to someone. Use when user says send, email, mail this to.",
        "parameters": {
            "to": "recipient email address",
            "subject": "email subject line",
            "body": "full email body text",
            "cc": "optional CC email address"
        }
    },
    {
        "name": "draft_email",
        "description": "Draft an email without sending. Use when user says draft, write an email, prepare an email.",
        "parameters": {
            "to": "recipient email address",
            "subject": "email subject line",
            "body": "full email body text"
        }
    },
    {
        "name": "open_file",
        "description": "Open and read a file from the agent workspace. Use when user says open, read this file, show me the file.",
        "parameters": {
            "file_path": "filename (files are stored in the agent workspace)"
        }
    },
    {
        "name": "create_file",
        "description": "Create a new file with content. Use when user says create a file, save this as, write to a file.",
        "parameters": {
            "file_path": "filename to create",
            "content": "text content to write",
            "file_type": "txt or docx"
        }
    },
    {
        "name": "list_directory",
        "description": "List files in the agent workspace. Use when user says show files, what files are there, list files.",
        "parameters": {
            "directory_path": "subdirectory name (optional, defaults to root workspace)",
            "extension_filter": "optional file extension filter like .pdf"
        }
    },
    {
        "name": "web_search",
        "description": "Search the internet. Use when user asks about current laws, recent cases, or anything outside uploaded documents.",
        "parameters": {
            "query": "search query string",
            "max_results": "number of results default 5"
        }
    },
    {
        "name": "create_reminder",
        "description": "Create a calendar reminder for a deadline or meeting. Use when user says remind me, set a reminder, add to calendar.",
        "parameters": {
            "title": "reminder title",
            "date": "date in YYYY-MM-DD format",
            "description": "optional description",
            "output_path": "filename for the .ics file (defaults to reminder.ics)"
        }
    },
    {
        "name": "summarize_document",
        "description": "Summarize an uploaded LexBot document. Use when user says summarize, give me a summary of, brief me on.",
        "parameters": {
            "document_name": "exact filename of the uploaded document",
            "user_id": "current user ID (auto-filled)"
        }
    }
]
