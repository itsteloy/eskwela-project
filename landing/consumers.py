import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time dashboard updates.
    All connected admin and teacher dashboards share the same broadcast group.

    Handles:
    - Student status changes
    - Announcements CRUD
    - Assignments CRUD
    - Submissions grading
    - Schedule updates
    - Module updates
    - Real-time notifications
    """

    GROUP_NAME = "dashboard_updates"

    async def connect(self):
        """Handle WebSocket connection"""
        # Only allow authenticated users
        if not self.scope["user"].is_authenticated:
            logger.warning("Unauthenticated WebSocket connection attempt")
            await self.close()
            return

        user = self.scope["user"]
        logger.info(f"WebSocket connected: {user.username} ({user.id})")

        # Join the shared dashboard group
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

        # Send a welcome message so the client knows the connection is live
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connected",
                    "message": "Real-time sync active",
                    "user": user.username,
                    "timestamp": str(__import__("datetime").datetime.now()),
                }
            )
        )
        logger.info(f"User {user.username} added to dashboard_updates group")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        user = self.scope["user"]
        logger.info(f"WebSocket disconnected: {user.username} (code: {close_code})")
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    # ================================================================== #
    #  Receive message from WebSocket client (browser → server)          #
    # ================================================================== #
    async def receive(self, text_data):
        """Handle messages from the client"""
        try:
            data = json.loads(text_data)
            event_type = data.get("type", "unknown")

            # List of valid event types
            valid_types = {
                "student_status_changed",
                "student_registered",
                "announcement_created",
                "announcement_updated",
                "announcement_deleted",
                "assignment_created",
                "assignment_updated",
                "assignment_deleted",
                "assignment_submitted",
                "schedule_created",
                "schedule_updated",
                "schedule_deleted",
                "module_created",
                "module_updated",
                "module_deleted",
                "submission_graded",
                "student_enrolled",
                "ping",
            }

            if event_type not in valid_types:
                logger.warning(f"Invalid event type received: {event_type}")
                return

            logger.debug(f"Broadcasting event: {event_type}")

            # Broadcast to all connected clients
            await self.channel_layer.group_send(
                self.GROUP_NAME,
                {
                    "type": "broadcast_update",
                    "payload": data,
                },
            )
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from client")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")

    # ================================================================== #
    #  Receive message from channel layer (server → WebSocket client)    #
    # ================================================================== #
    async def broadcast_update(self, event):
        """Forward group messages to the WebSocket client"""
        try:
            await self.send(text_data=json.dumps(event["payload"]))
        except Exception as e:
            logger.error(f"Error sending message to client: {str(e)}")
