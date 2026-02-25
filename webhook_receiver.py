"""Webhook receiver for Drupal content change notifications."""

import hashlib
import hmac
import logging
import os
from datetime import datetime
from typing import Dict, Optional

from flask import Flask, request, jsonify

import config
from main import StaticSiteUpdater

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Webhook secret for validation (set via environment variable)
WEBHOOK_SECRET = os.getenv("DRUPAL_WEBHOOK_SECRET", "")


def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    """Validate the webhook signature using HMAC.

    Args:
        payload: Raw request body
        signature: Signature from request header

    Returns:
        True if signature is valid
    """
    if not WEBHOOK_SECRET:
        logger.warning("No webhook secret configured - skipping validation")
        return True

    # Drupal Webhooks module typically sends signature as 'sha256=<hash>'
    if signature.startswith('sha256='):
        signature = signature[7:]

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


def map_drupal_content_type(drupal_type: str) -> Optional[str]:
    """Map Drupal content type to internal content type identifier.

    Args:
        drupal_type: Drupal content type (e.g., 'node--page')

    Returns:
        Internal content type identifier or None if not found
    """
    # Check if it's already in the correct format
    if drupal_type in config.CONTENT_TYPES.values():
        return drupal_type

    # Try to find it by key
    for key, value in config.CONTENT_TYPES.items():
        if value == drupal_type or key == drupal_type:
            return value

    return None


@app.route('/webhook/drupal', methods=['POST'])
def receive_webhook():
    """Handle incoming Drupal webhook notifications.

    Expected payload format:
    {
        "event": "entity.update" | "entity.create" | "entity.delete",
        "entity_type": "node",
        "bundle": "page",
        "entity_id": "uuid-here",
        "entity_uuid": "uuid-here",
        "changed": "2026-02-25T12:00:00Z",
        "title": "Page Title"
    }

    Returns:
        JSON response with processing status
    """
    # Validate signature if secret is configured
    signature = request.headers.get('X-Drupal-Signature', '')
    if WEBHOOK_SECRET and not validate_webhook_signature(request.data, signature):
        logger.warning("Invalid webhook signature received")
        return jsonify({"error": "Invalid signature"}), 401

    # Parse webhook payload
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid JSON payload"}), 400
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    # Extract event details
    event = payload.get('event', '')
    entity_type = payload.get('entity_type', '')
    bundle = payload.get('bundle', '')
    entity_id = payload.get('entity_uuid') or payload.get('entity_id', '')
    changed = payload.get('changed', '')
    title = payload.get('title', 'Unknown')

    logger.info(
        f"Received webhook: event={event}, type={entity_type}, "
        f"bundle={bundle}, id={entity_id}, title={title}"
    )

    # Construct content type identifier
    content_type = f"{entity_type}--{bundle}" if bundle else entity_type

    # Map to internal content type
    mapped_type = map_drupal_content_type(content_type)
    if not mapped_type:
        logger.warning(f"Unknown content type: {content_type}")
        return jsonify({
            "status": "ignored",
            "message": f"Content type '{content_type}' not tracked"
        }), 200

    # Handle different event types
    try:
        if event in ['entity.update', 'entity.create', 'node.update', 'node.create']:
            # Process the content update
            result = process_content_update(mapped_type, entity_id, title)
            return jsonify(result), 200

        elif event in ['entity.delete', 'node.delete']:
            # Handle content deletion
            result = process_content_deletion(mapped_type, entity_id, title)
            return jsonify(result), 200

        else:
            logger.warning(f"Unknown event type: {event}")
            return jsonify({
                "status": "ignored",
                "message": f"Unknown event type: {event}"
            }), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def process_content_update(content_type: str, content_id: str, title: str) -> Dict:
    """Process a content update event.

    Args:
        content_type: Content type identifier
        content_id: Content UUID
        title: Content title

    Returns:
        Processing result dictionary
    """
    logger.info(f"Processing update for {content_type}/{content_id}: {title}")

    try:
        # Initialize the updater
        updater = StaticSiteUpdater()

        # Process this specific content item
        stats = {
            "pages_checked": 0,
            "pages_updated": 0,
            "facilities_checked": 0,
            "facilities_updated": 0,
            "personnel_checked": 0,
            "personnel_updated": 0,
            "procedures_checked": 0,
            "procedures_updated": 0,
        }

        success = updater._process_content_item(
            content_type, content_id, stats
        )

        if success:
            logger.info(f"Successfully processed {content_type}/{content_id}")
            return {
                "status": "success",
                "message": f"Content '{title}' processed successfully",
                "content_type": content_type,
                "content_id": content_id,
                "stats": stats
            }
        else:
            logger.error(f"Failed to process {content_type}/{content_id}")
            return {
                "status": "error",
                "message": f"Failed to process content '{title}'",
                "content_type": content_type,
                "content_id": content_id
            }

    except Exception as e:
        logger.error(f"Error processing content update: {e}", exc_info=True)
        raise


def process_content_deletion(content_type: str, content_id: str, title: str) -> Dict:
    """Process a content deletion event.

    Args:
        content_type: Content type identifier
        content_id: Content UUID
        title: Content title

    Returns:
        Processing result dictionary
    """
    logger.info(f"Processing deletion for {content_type}/{content_id}: {title}")

    # TODO: Implement deletion handling
    # This would typically:
    # 1. Mark the content as deleted in the dependency mapper
    # 2. Remove the generated HTML from S3
    # 3. Regenerate any pages that referenced this content
    # 4. Update sitemaps/indexes

    logger.warning("Content deletion handling not yet implemented")

    return {
        "status": "acknowledged",
        "message": f"Deletion of '{title}' acknowledged but not fully implemented",
        "content_type": content_type,
        "content_id": content_id
    }


@app.route('/webhook/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_secret_configured": bool(WEBHOOK_SECRET)
    }), 200


@app.route('/webhook/trigger-full-sync', methods=['POST'])
def trigger_full_sync():
    """Manually trigger a full sync of all content.

    This endpoint allows manual triggering of a complete site regeneration.
    Should be protected with authentication in production.
    """
    # Validate signature
    signature = request.headers.get('X-Drupal-Signature', '')
    if WEBHOOK_SECRET and not validate_webhook_signature(request.data, signature):
        logger.warning("Invalid signature for full sync request")
        return jsonify({"error": "Invalid signature"}), 401

    logger.info("Full sync triggered via webhook")

    try:
        updater = StaticSiteUpdater()

        # Check for all unprocessed changes
        stats = updater.check_and_process_changes()

        return jsonify({
            "status": "success",
            "message": "Full sync completed",
            "stats": stats
        }), 200

    except Exception as e:
        logger.error(f"Error during full sync: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    # Development server
    # For production, use a WSGI server like Gunicorn or uWSGI
    port = int(os.getenv('WEBHOOK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting webhook receiver on port {port}")
    logger.info(f"Webhook secret configured: {bool(WEBHOOK_SECRET)}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
