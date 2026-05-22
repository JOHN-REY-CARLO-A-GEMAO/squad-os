"""
TelegramTool — send and receive messages via Telegram Bot API.

Requires:
- TELEGRAM_BOT_TOKEN in environment or .env
- Optional: TELEGRAM_CHAT_ID for direct messaging
"""
import asyncio
import json
import os
from typing import Optional, List
from squad_os.tools.base import BaseTool


class TelegramTool(BaseTool):
    name = "send_telegram"
    description = (
        "Send a message to a Telegram chat or user. Requires a valid Telegram bot token. "
        "Can send text messages, and optionally parse as Markdown or HTML. "
        "Use chat_id to target specific chats, or omit to use the default chat."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message text to send"
            },
            "chat_id": {
                "type": "string",
                "description": "Telegram chat ID (optional, uses default if omitted)"
            },
            "parse_mode": {
                "type": "string",
                "enum": ["Markdown", "HTML", "MarkdownV2"],
                "description": "Message parsing mode (optional)"
            }
        },
        "required": ["message"]
    }

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.default_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    async def execute(self, message: str, chat_id: Optional[str] = None, parse_mode: Optional[str] = None) -> str:
        if not self.bot_token:
            return "Error: TELEGRAM_BOT_TOKEN not set in environment."

        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            return "Error: No chat_id provided and TELEGRAM_CHAT_ID not set."

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": message
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        return f"Message sent to Telegram chat {target_chat}."
                    else:
                        return f"Telegram API error: {data.get('description', 'Unknown error')}"
        except ImportError:
            return "Error: aiohttp is required. Install with: pip install aiohttp"
        except Exception as e:
            return f"Error sending Telegram message: {e}"


class TelegramReceiveTool(BaseTool):
    name = "receive_telegram"
    description = (
        "Poll for new messages from Telegram. Returns the latest messages from the bot's updates. "
        "Use offset to skip previously seen messages."
    )
    parameters = {
        "type": "object",
        "properties": {
            "offset": {
                "type": "integer",
                "description": "Update offset to skip already processed messages"
            },
            "limit": {
                "type": "integer",
                "description": "Max number of updates to retrieve (default 10)"
            },
            "timeout": {
                "type": "integer",
                "description": "Long polling timeout in seconds (default 30)"
            }
        },
        "required": []
    }

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    async def execute(self, offset: int = 0, limit: int = 10, timeout: int = 30) -> str:
        if not self.bot_token:
            return "Error: TELEGRAM_BOT_TOKEN not set in environment."

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "offset": offset,
            "limit": limit,
            "timeout": timeout
        }

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        updates = data.get("result", [])
                        if not updates:
                            return "No new messages."
                        
                        messages = []
                        for update in updates:
                            msg = update.get("message", {})
                            chat = msg.get("chat", {})
                            messages.append({
                                "update_id": update.get("update_id"),
                                "chat_id": chat.get("id"),
                                "chat_name": chat.get("first_name", chat.get("title", "Unknown")),
                                "text": msg.get("text", ""),
                                "date": msg.get("date")
                            })
                        return json.dumps(messages, indent=2)
                    else:
                        return f"Telegram API error: {data.get('description', 'Unknown error')}"
        except ImportError:
            return "Error: aiohttp is required. Install with: pip install aiohttp"
        except Exception as e:
            return f"Error receiving Telegram messages: {e}"
