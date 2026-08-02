import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

GROUP_NAME = "dashboard_updates"


def broadcast_event(event_type: str, data: dict = None):
    """
    Send a real-time event to every connected dashboard WebSocket client.

    This function uses Django Channels to broadcast events asynchronously.
    If Channels is not properly configured, events are silently ignored
    (so views continue to work normally).

    Args:
        event_type (str): One of the recognized event type strings, e.g.
                         'announcement_created', 'student_status_changed', etc.
        data (dict):      Optional dict of extra payload fields sent to clients.

    Example:
        >>> broadcast_event('student_status_changed', {
        ...     'id': 42,
        ...     'status': 'approved',
        ...     'name': 'John Doe'
        ... })
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning(
                "Channel layer not configured. Real-time updates disabled. "
                "Please ensure Django Channels is properly installed and configured."
            )
            return

        payload = {"type": event_type}
        if data:
            payload.update(data)

        logger.debug(f"Broadcasting event: {event_type} with data: {data}")

        # Send the message to the group
        async_to_sync(channel_layer.group_send)(
            GROUP_NAME,
            {
                "type": "broadcast_update",
                "payload": payload,
            },
        )
        logger.info(f"Event '{event_type}' broadcasted successfully")

    except Exception as e:
        logger.error(
            f"Error broadcasting event '{event_type}': {str(e)}", exc_info=True
        )
        # Don't raise exception; allow views to continue working
