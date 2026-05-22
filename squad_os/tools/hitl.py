"""
RichApprovalTool — structured HITL approval forms with WebSocket notifications.

Features:
- Rich structured forms (select, text, number, boolean fields)
- WebSocket push notifications to connected clients
- Real-time interrupt handling for agent tasks
- Approval workflows with context and guidance
"""
import asyncio
import json
import os
import time
from typing import Optional, List, Dict, Any
from squad_os.tools.base import BaseTool
from squad_os.database.session import DB_PATH
import aiosqlite


class HITLWebSocketServer:
    """WebSocket server for real-time HITL notifications."""
    
    _instance = None
    _connections = set()
    _server = None
    _port = int(os.getenv("HITL_WS_PORT", "8765"))
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def start(self):
        """Start the WebSocket server."""
        import aiohttp
        from aiohttp import web
        
        async def websocket_handler(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            self._connections.add(ws)
            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        # Handle approval responses
                        if data.get("type") == "approval_response":
                            await self._handle_approval_response(data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break
            finally:
                self._connections.discard(ws)
            return ws
        
        app = web.Application()
        app.router.add_get("/ws", websocket_handler)
        
        # Health check endpoint
        async def health(request):
            return web.Response(text=json.dumps({"status": "ok", "connections": len(self._connections)}))
        app.router.add_get("/health", health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", self._port)
        await site.start()
        print(f"📡 [HITL]: WebSocket server running on ws://localhost:{self._port}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected WebSocket clients."""
        if not self._connections:
            return
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._connections -= dead
    
    async def _handle_approval_response(self, data: dict):
        """Handle an approval response from a WebSocket client."""
        approval_id = data.get("approval_id")
        decision = data.get("decision", "REJECTED")
        feedback = data.get("feedback", "")
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE approvals SET status = ?, feedback = ? WHERE id = ?",
                (decision, feedback, approval_id)
            )
            await db.commit()


class RichApprovalForm:
    """Builder for structured approval forms."""
    
    @staticmethod
    def create_select_field(
        label: str,
        options: List[str],
        description: str = "",
        required: bool = True
    ) -> dict:
        return {
            "type": "select",
            "label": label,
            "options": options,
            "description": description,
            "required": required
        }
    
    @staticmethod
    def create_text_field(
        label: str,
        placeholder: str = "",
        description: str = "",
        required: bool = True
    ) -> dict:
        return {
            "type": "text",
            "label": label,
            "placeholder": placeholder,
            "description": description,
            "required": required
        }
    
    @staticmethod
    def create_number_field(
        label: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        description: str = "",
        required: bool = True
    ) -> dict:
        return {
            "type": "number",
            "label": label,
            "min": min_value,
            "max": max_value,
            "description": description,
            "required": required
        }
    
    @staticmethod
    def create_boolean_field(label: str, description: str = "") -> dict:
        return {
            "type": "boolean",
            "label": label,
            "description": description,
            "required": True
        }
    
    @staticmethod
    def create_approval_request(
        title: str,
        message: str,
        fields: List[dict],
        context: Optional[str] = None
    ) -> dict:
        return {
            "type": "approval_request",
            "title": title,
            "message": message,
            "fields": fields,
            "context": context,
            "created_at": time.time()
        }


class RichApprovalTool(BaseTool):
    name = "request_approval"
    description = (
        "Request human approval with a structured form. Supports select dropdowns, text input, "
        "number fields, and boolean choices. Use this when you need the human to make a decision "
        "or provide structured input. Sends a real-time notification to the dashboard."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the approval request"
            },
            "message": {
                "type": "string",
                "description": "Message to show the human explaining what needs approval"
            },
            "fields_json": {
                "type": "string",
                "description": "JSON array of form fields. Each field is an object with: type (select|text|number|boolean), label, options (for select), placeholder (for text), description, required"
            },
            "context": {
                "type": "string",
                "description": "Optional context data for the human"
            }
        },
        "required": ["title", "message", "fields_json"]
    }
    category = "hitl"

    async def execute(
        self,
        title: str,
        message: str,
        fields_json: str,
        context: Optional[str] = None
    ) -> str:
        try:
            fields = json.loads(fields_json)
        except json.JSONDecodeError:
            return "Error: fields_json must be valid JSON array."
        
        if not isinstance(fields, list):
            return "Error: fields_json must be a JSON array."
        
        form = RichApprovalForm.create_approval_request(title, message, fields, context)
        
        # Store in database
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO approvals (mission_id, task_id, message, status) VALUES (?, ?, ?, 'PENDING')",
                (0, 0, json.dumps(form))
            )
            approval_id = cursor.lastrowid
            await db.commit()
        
        form["approval_id"] = approval_id
        
        # Push WebSocket notification
        ws_server = HITLWebSocketServer.get_instance()
        await ws_server.broadcast(form)
        
        # Wait for response (polling fallback)
        start_time = time.time()
        timeout = int(os.getenv("HITL_TIMEOUT_SECONDS", "300"))
        
        while time.time() - start_time < timeout:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT status, feedback FROM approvals WHERE id = ?",
                    (approval_id,)
                )
                row = await cursor.fetchone()
                if row and row[0] != "PENDING":
                    decision = "APPROVED" if row[0] == "APPROVED" else "REJECTED"
                    feedback = row[1] or ""
                    result = {
                        "decision": decision,
                        "feedback": feedback,
                        "approval_id": approval_id
                    }
                    return json.dumps(result, indent=2)
            await asyncio.sleep(1)
        
        return json.dumps({
            "decision": "TIMEOUT",
            "feedback": "Approval request timed out.",
            "approval_id": approval_id
        }, indent=2)


class NotifyHumanTool(BaseTool):
    name = "notify_human"
    description = (
        "Send a real-time notification to the human via WebSocket. "
        "Use this for status updates, alerts, and non-blocking messages. "
        "The human sees this on the dashboard without needing to respond."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Notification title"
            },
            "message": {
                "type": "string",
                "description": "Notification message body"
            },
            "level": {
                "type": "string",
                "enum": ["info", "warning", "error", "success"],
                "description": "Notification severity level"
            }
        },
        "required": ["title", "message"]
    }
    category = "hitl"

    async def execute(
        self,
        title: str,
        message: str,
        level: str = "info"
    ) -> str:
        notification = {
            "type": "notification",
            "title": title,
            "message": message,
            "level": level,
            "created_at": time.time()
        }
        
        ws_server = HITLWebSocketServer.get_instance()
        await ws_server.broadcast(notification)
        
        return f"Notification sent: {title} ({level})"


class HITLInterruptTool(BaseTool):
    name = "interrupt_for_guidance"
    description = (
        "Pause execution and request human guidance. Use this when you encounter an "
        "ambiguous situation, need clarification, or face an error you can't resolve. "
        "The human can provide guidance to help you continue."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Question or guidance request for the human"
            },
            "context": {
                "type": "string",
                "description": "Context about what the agent was doing when interrupted"
            },
            "options_json": {
                "type": "string",
                "description": "JSON array of suggested options for the human to choose from (optional)"
            }
        },
        "required": ["question", "context"]
    }
    category = "hitl"

    async def execute(
        self,
        question: str,
        context: str,
        options_json: Optional[str] = None
    ) -> str:
        from squad_os.database.session import create_interrupt
        
        options = []
        if options_json:
            try:
                options = json.loads(options_json)
            except json.JSONDecodeError:
                pass
        
        interrupt_data = {
            "type": "interrupt",
            "question": question,
            "context": context,
            "options": options,
            "created_at": time.time()
        }
        
        interrupt_id = await create_interrupt(
            mission_id=0,
            task_idx=0,
            context=json.dumps(interrupt_data),
            error_message=question
        )
        
        interrupt_data["interrupt_id"] = interrupt_id
        
        # Push WebSocket notification
        ws_server = HITLWebSocketServer.get_instance()
        await ws_server.broadcast(interrupt_data)
        
        # Wait for guidance (polling fallback)
        start_time = time.time()
        timeout = int(os.getenv("HITL_TIMEOUT_SECONDS", "300"))
        
        while time.time() - start_time < timeout:
            from squad_os.database.session import get_pending_interrupt
            result = await get_pending_interrupt(0)
            if result and result['status'] != 'PENDING':
                return json.dumps({
                    "status": "guidance_received",
                    "guidance": result.get('user_guidance', ''),
                    "interrupt_id": interrupt_id
                }, indent=2)
            await asyncio.sleep(1)
        
        return json.dumps({
            "status": "timeout",
            "guidance": "",
            "interrupt_id": interrupt_id
        }, indent=2)
