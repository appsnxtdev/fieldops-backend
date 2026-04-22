import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_firebase_initialized = False


def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK (call once on startup)."""
    global _firebase_initialized

    if _firebase_initialized:
        return

    settings = get_settings()

    if not settings.FIREBASE_PROJECT_ID or not settings.FIREBASE_CREDENTIALS_PATH:
        logger.warning("Firebase credentials not configured - FCM disabled")
        return

    cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
    if not cred_path.exists():
        logger.error(f"Firebase credentials file not found: {cred_path}")
        return

    try:
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")


async def send_fcm_message(token: str, title: str, body: str, data: dict) -> bool:
    """
    Send FCM message to a device token.

    Args:
        token: FCM device token
        title: Notification title
        body: Notification body
        data: Custom data payload

    Returns:
        True if sent successfully, False if token is invalid or error occurred
    """
    if not _firebase_initialized:
        logger.warning("Firebase not initialized - skipping FCM send")
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in data.items()},  # All values must be strings
            token=token,
        )
        messaging.send(message)
        logger.info(f"FCM message sent to token: {token[:10]}...")
        return True
    except messaging.UnregisteredError:
        logger.warning(f"FCM token is invalid/unregistered: {token[:10]}...")
        return False
    except Exception as e:
        logger.error(f"FCM send error: {e}")
        return False
