"""
DiscordTool — send messages to Discord channels via webhook or bot API.

Requires:
- DISCORD_WEBHOOK_URL for webhook-based messaging (simplest)
- OR DISCORD_BOT_TOKEN for bot-based messaging
"""
import asyncio
import json
import os
from typing import Optional
from squad_os.tools.base import BaseTool


class DiscordTool(BaseTool):
    name = "send_discord"
    description = (
        "Send a message to a Discord channel. Supports webhooks (simplest) or bot API. "
        "Can send plain text, embeds, or formatted messages. "
        "Set DISCORD_WEBHOOK_URL in environment for webhook mode, "
        "or DISCORD_BOT_TOKEN + channel_id for bot mode."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message text to send"
            },
            "channel_id": {
                "type": "string",
                "description": "Discord channel ID (required for bot mode, ignored for webhook)"
            },
            "username": {
                "type": "string",
                "description": "Username to display (webhook mode only)"
            },
            "embed_title": {
                "type": "string",
                "description": "Embed title (optional, creates rich embed if provided)"
            },
            "embed_description": {
                "type": "string",
                "description": "Embed description (optional)"
            },
            "embed_color": {
                "type": "integer",
                "description": "Embed color as decimal (e.g., 0x00ff00 = 65280)"
            }
        },
        "required": ["message"]
    }

    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN")

    async def execute(
        self,
        message: str,
        channel_id: Optional[str] = None,
        username: Optional[str] = None,
        embed_title: Optional[str] = None,
        embed_description: Optional[str] = None,
        embed_color: Optional[int] = None
    ) -> str:
        payload = {"content": message}
        
        if username:
            payload["username"] = username
        
        if embed_title or embed_description:
            embed = {}
            if embed_title:
                embed["title"] = embed_title
            if embed_description:
                embed["description"] = embed_description
            if embed_color:
                embed["color"] = embed_color
            payload["embeds"] = [embed]

        # Webhook mode (simplest)
        if self.webhook_url:
            return await self._send_webhook(payload)
        
        # Bot mode
        if self.bot_token and channel_id:
            return await self._send_bot_message(channel_id, payload)
        
        return "Error: Set DISCORD_WEBHOOK_URL or (DISCORD_BOT_TOKEN + channel_id)."

    async def _send_webhook(self, payload: dict) -> str:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status in (200, 204):
                        return "Message sent to Discord via webhook."
                    else:
                        text = await resp.text()
                        return f"Discord webhook error ({resp.status}): {text}"
        except ImportError:
            return "Error: aiohttp is required. Install with: pip install aiohttp"
        except Exception as e:
            return f"Error sending Discord webhook: {e}"

    async def _send_bot_message(self, channel_id: str, payload: dict) -> str:
        try:
            import aiohttp
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json"
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return f"Message sent to Discord channel {channel_id} via bot."
                    else:
                        text = await resp.text()
                        return f"Discord bot error ({resp.status}): {text}"
        except ImportError:
            return "Error: aiohttp is required. Install with: pip install aiohttp"
        except Exception as e:
            return f"Error sending Discord bot message: {e}"


class DiscordReceiveTool(BaseTool):
    name = "receive_discord"
    description = (
        "Poll for new messages in a Discord channel. Requires bot token and channel ID. "
        "Returns recent messages with author, content, and timestamp."
    )
    parameters = {
        "type": "object",
        "properties": {
            "channel_id": {
                "type": "string",
                "description": "Discord channel ID to poll"
            },
            "limit": {
                "type": "integer",
                "description": "Max number of messages to retrieve (default 10)"
            }
        },
        "required": ["channel_id"]
    }

    def __init__(self):
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN")

    async def execute(self, channel_id: str, limit: int = 10) -> str:
        if not self.bot_token:
            return "Error: DISCORD_BOT_TOKEN not set in environment."

        try:
            import aiohttp
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json"
            }
            params = {"limit": limit}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 200:
                        messages = await resp.json()
                        if not messages:
                            return "No recent messages."
                        
                        result = []
                        for msg in messages:
                            author = msg.get("author", {})
                            result.append({
                                "id": msg.get("id"),
                                "author": author.get("username", "Unknown"),
                                "content": msg.get("content", ""),
                                "timestamp": msg.get("timestamp")
                            })
                        return json.dumps(result, indent=2)
                    else:
                        text = await resp.text()
                        return f"Discord bot error ({resp.status}): {text}"
        except ImportError:
            return "Error: aiohttp is required. Install with: pip install aiohttp"
        except Exception as e:
            return f"Error receiving Discord messages: {e}"
