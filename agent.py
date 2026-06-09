import json
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sqlalchemy import select

import config
from database import Message, async_session_factory
from agent_tools import (
    send_email, draft_email, open_file, create_file,
    list_directory, web_search, create_reminder,
    summarize_document, TOOL_REGISTRY
)

logger = logging.getLogger(__name__)


AGENT_SYSTEM_PROMPT = """You are LexBot Agent — an intelligent legal assistant that can take actions.

You have FULL MEMORY of the current conversation. You can see every message exchanged so far in this session. When the user refers to something said earlier — like "that", "it", "the above", "the first one", "my client", or any previously mentioned detail — look back through the conversation history to understand what they mean. Never ask the user to repeat information they already provided in this session.

You have access to these tools:
{tool_descriptions}

When the user gives you a command, return ONLY a valid JSON object in this exact format:

{{
  "thought": "brief explanation of what you are doing",
  "tool": "tool_name_here",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}

If no tool is needed and you can answer directly:
{{
  "thought": "this is a direct question I can answer",
  "tool": "none",
  "answer": "your direct answer here"
}}

Rules:
- Return ONLY the JSON object with no extra text and no markdown
- Use exact tool names from the list
- Never make up file paths, ask the user if unclear
- Always use draft_email first unless user explicitly says send
- Do not include user_id in parameters, it is auto-filled
- Use conversation history to resolve references to previous messages and results
"""


AGENT_MAX_HISTORY = 20


class LexBotAgent:

    def __init__(self):
        self._llm = ChatGroq(
            api_key=config.GROQ_API_KEY,
            model=config.GROQ_MODEL,
            temperature=0,
        )

    def _build_tool_descriptions(self) -> str:
        lines = []
        for tool in TOOL_REGISTRY:
            params = ", ".join(f"{k}: {v}" for k, v in tool["parameters"].items())
            lines.append(f"- {tool['name']}({params}): {tool['description']}")
        return "\n".join(lines)

    def _extract_json(self, raw: str) -> dict:
        """Robustly extract JSON from LLM response, handling markdown fences and extra text."""
        text = raw.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")

    # ── Memory helpers ─────────────────────────────────────────────────────────

    async def _load_history(self, user_id: int, session_id: str) -> list[dict]:
        """Load recent agent conversation history from the messages table."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Message.role, Message.content, Message.created_at)
                .where(
                    Message.user_id == user_id,
                    Message.session_id == session_id,
                )
                .order_by(Message.created_at.desc())
                .limit(AGENT_MAX_HISTORY)
            )
            rows = result.all()
            # Reverse so oldest comes first
            return [
                {"role": r.role, "content": r.content}
                for r in reversed(rows)
            ]

    async def _save_message(self, user_id: int, session_id: str, role: str, content: str) -> None:
        """Save a single message to the messages table."""
        async with async_session_factory() as session:
            try:
                msg = Message(
                    user_id=user_id,
                    session_id=session_id,
                    role=role,
                    content=content,
                )
                session.add(msg)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error("Failed to save agent message: %s", exc)

    def _build_messages(self, system_prompt: str, history: list[dict], current_command: str) -> list:
        """Build a LangChain message list from system prompt, history, and current command."""
        messages = [SystemMessage(content=system_prompt)]

        for entry in history:
            if entry["role"] == "human":
                messages.append(HumanMessage(content=entry["content"]))
            else:
                messages.append(AIMessage(content=entry["content"]))

        messages.append(HumanMessage(content=current_command))
        return messages

    def _format_assistant_summary(self, result: dict) -> str:
        """Create a human-readable summary of the agent's action for conversation history."""
        tool_used = result.get("tool_used", "none")
        thought = result.get("thought", "")
        success = result.get("success", False)

        if tool_used == "none":
            # Direct answer — store the answer itself
            return result.get("result", thought or "I answered directly.")

        if not success:
            error = result.get("error", "Unknown error")
            return f"I tried to use {tool_used} but it failed: {error}"

        raw_result = result.get("result", "")
        if isinstance(raw_result, dict):
            # Summarize structured results
            result_str = json.dumps(raw_result, indent=2)
            # Truncate if very long to keep history manageable
            if len(result_str) > 1500:
                result_str = result_str[:1500] + "\n... (truncated)"
            return f"I used {tool_used}. {thought}\n\nResult:\n{result_str}"
        else:
            text = str(raw_result)
            if len(text) > 1500:
                text = text[:1500] + "\n... (truncated)"
            return f"I used {tool_used}. {thought}\n\nResult: {text}"

    # ── Main run method ────────────────────────────────────────────────────────

    async def run(self, command: str, user_id: int, session_id: str, context: str = "") -> dict:
        tool_descriptions = self._build_tool_descriptions()
        system = AGENT_SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

        user_message = command
        if context:
            user_message = f"Context: {context}\n\nCommand: {command}"

        # 1. Load conversation history
        history = await self._load_history(user_id, session_id)

        # 2. Build full message list with history
        messages = self._build_messages(system, history, user_message)

        # 3. Save the user's command to DB
        await self._save_message(user_id, session_id, "human", user_message)

        # 4. Call LLM with full conversation context
        try:
            response = await self._llm.ainvoke(messages)
            raw = response.content.strip()
            decision = self._extract_json(raw)
        except Exception as e:
            logger.error("Agent decision parsing failed: %s", e)
            error_result = {
                "success": False,
                "thought": "Could not parse agent decision.",
                "error": str(e),
                "session_id": session_id,
            }
            # Save error as assistant message
            await self._save_message(user_id, session_id, "assistant", f"Error: {str(e)}")
            return error_result

        tool_name = decision.get("tool", "none")
        thought = decision.get("thought", "")
        params = decision.get("parameters", {})

        if tool_name == "none":
            result = {
                "success": True,
                "thought": thought,
                "tool_used": "none",
                "result": decision.get("answer", ""),
                "session_id": session_id,
            }
            # 5. Save assistant response to DB
            await self._save_message(user_id, session_id, "assistant", self._format_assistant_summary(result))
            return result

        tool_result = await self._execute_tool(tool_name, params, user_id)
        result = {
            "success": tool_result.get("success", False),
            "thought": thought,
            "tool_used": tool_name,
            "parameters_used": params,
            "result": tool_result.get("result", ""),
            "error": tool_result.get("error", ""),
            "session_id": session_id,
        }

        # 5. Save assistant response to DB
        await self._save_message(user_id, session_id, "assistant", self._format_assistant_summary(result))
        return result

    async def _execute_tool(self, tool_name: str, params: dict, user_id: int) -> dict:
        """Execute the selected tool with validated parameters."""
        try:
            if tool_name == "send_email":
                return send_email(
                    to=params.get("to", ""),
                    subject=params.get("subject", ""),
                    body=params.get("body", ""),
                    cc=params.get("cc", ""),
                )
            elif tool_name == "draft_email":
                return draft_email(
                    to=params.get("to", ""),
                    subject=params.get("subject", ""),
                    body=params.get("body", ""),
                )
            elif tool_name == "open_file":
                return open_file(file_path=params.get("file_path", ""))
            elif tool_name == "create_file":
                return create_file(
                    file_path=params.get("file_path", ""),
                    content=params.get("content", ""),
                    file_type=params.get("file_type", "txt"),
                )
            elif tool_name == "list_directory":
                return list_directory(
                    directory_path=params.get("directory_path", ""),
                    extension_filter=params.get("extension_filter", ""),
                )
            elif tool_name == "web_search":
                return web_search(
                    query=params.get("query", ""),
                    max_results=int(params.get("max_results", 5)),
                )
            elif tool_name == "create_reminder":
                return create_reminder(
                    title=params.get("title", ""),
                    date=params.get("date", ""),
                    description=params.get("description", ""),
                    output_path=params.get("output_path", "reminder.ics"),
                )
            elif tool_name == "summarize_document":
                return await summarize_document(
                    document_name=params.get("document_name", ""),
                    user_id=user_id,
                )
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error("Tool '%s' execution failed: %s", tool_name, e)
            return {"success": False, "error": f"Tool '{tool_name}' failed: {str(e)}"}


agent = LexBotAgent()
