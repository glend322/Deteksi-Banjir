import os
import logging
from typing import Optional
from firebase_admin import credentials, initialize_app, messaging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _init_firebase():
    """Initialize Firebase Admin SDK lazily (only once)."""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if not cred_path or not os.path.exists(cred_path):
        logger.warning("[FCM] Firebase credentials not configured — push notifications disabled.")
        return False

    try:
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
        _firebase_initialized = True
        logger.info("[FCM] Firebase Admin SDK initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"[FCM] Failed to initialize Firebase: {e}")
        return False


def send_push_notification(
    user_id: int,
    title: str,
    body: str,
    data: Optional[dict] = None,
    db: Optional[Session] = None,
) -> bool:
    """
    Send a push notification to a single user via FCM.
    Returns True if sent successfully, False otherwise.
    """
    if not _init_firebase():
        return False

    if not db:
        from app.core.database import SessionLocal
        db = SessionLocal()
        _close_db = True
    else:
        _close_db = False

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.fcm_token or not user.notification_enabled:
            logger.debug(f"[FCM] User {user_id} has no FCM token or notifications disabled.")
            return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=user.fcm_token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="flood_alerts",
                    sound="default",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound="default",
                        badge=1,
                    )
                ),
            ),
        )

        response = messaging.send(message)
        logger.info(f"[FCM] Notification sent to user {user_id}: {response}")
        return True

    except messaging.UnregisteredError:
        logger.warning(f"[FCM] Token expired for user {user_id} — clearing token.")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.fcm_token = None
            db.commit()
        return False

    except Exception as e:
        logger.error(f"[FCM] Failed to send notification to user {user_id}: {e}")
        return False

    finally:
        if _close_db:
            db.close()


def send_broadcast_notification(
    title: str,
    body: str,
    data: Optional[dict] = None,
    db: Optional[Session] = None,
) -> int:
    """
    Send a push notification to ALL users with enabled notifications.
    Returns the count of successfully sent notifications.
    """
    if not _init_firebase():
        return 0

    if not db:
        from app.core.database import SessionLocal
        db = SessionLocal()
        _close_db = True
    else:
        _close_db = False

    try:
        users = db.query(User).filter(
            User.fcm_token.isnot(None),
            User.notification_enabled == True,
        ).all()

        if not users:
            return 0

        tokens = [u.fcm_token for u in users if u.fcm_token]
        if not tokens:
            return 0

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="flood_alerts",
                    sound="default",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound="default",
                        badge=1,
                    )
                ),
            ),
        )

        response = messaging.send_each_for_multicast(message)
        logger.info(f"[FCM] Broadcast sent: {response.success_count}/{len(tokens)} success")
        return response.success_count

    except Exception as e:
        logger.error(f"[FCM] Broadcast failed: {e}")
        return 0

    finally:
        if _close_db:
            db.close()
