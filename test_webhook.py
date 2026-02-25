#!/usr/bin/env python3
"""Test script for webhook receiver."""

import hashlib
import hmac
import json
import os
import sys
from typing import Dict

import requests


def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC signature for payload.

    Args:
        payload: JSON payload as string
        secret: Webhook secret

    Returns:
        Signature string with sha256= prefix
    """
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def test_health_endpoint(base_url: str) -> bool:
    """Test the health check endpoint.

    Args:
        base_url: Base URL of webhook receiver

    Returns:
        True if healthy
    """
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/webhook/health")
        response.raise_for_status()

        data = response.json()
        print(f"✓ Health check passed")
        print(f"  Status: {data['status']}")
        print(f"  Secret configured: {data['webhook_secret_configured']}")
        print(f"  Timestamp: {data['timestamp']}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_webhook_payload(
    base_url: str, secret: str, event_type: str = "entity.update"
) -> bool:
    """Test sending a webhook payload.

    Args:
        base_url: Base URL of webhook receiver
        secret: Webhook secret
        event_type: Type of event to simulate

    Returns:
        True if successful
    """
    print(f"\nTesting {event_type} webhook...")

    # Create test payload
    payload: Dict = {
        "event": event_type,
        "entity_type": "node",
        "bundle": "page",
        "entity_id": "123",
        "entity_uuid": "test-uuid-12345",
        "changed": "2026-02-25T12:00:00Z",
        "title": "Test Page",
    }

    payload_str = json.dumps(payload)
    signature = generate_signature(payload_str, secret)

    print(f"  Payload: {payload_str}")
    print(f"  Signature: {signature[:20]}...")

    try:
        response = requests.post(
            f"{base_url}/webhook/drupal",
            headers={
                "Content-Type": "application/json",
                "X-Drupal-Signature": signature,
            },
            data=payload_str,
        )

        print(f"  Response status: {response.status_code}")
        print(f"  Response body: {response.text}")

        if response.status_code == 200:
            result = response.json()
            if result.get("status") in ["success", "error", "ignored"]:
                print(f"✓ Webhook accepted: {result.get('message', 'No message')}")
                return True
            else:
                print(f"✗ Unexpected response: {result}")
                return False
        else:
            print(f"✗ Webhook rejected: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Webhook test failed: {e}")
        return False


def test_invalid_signature(base_url: str) -> bool:
    """Test that invalid signatures are rejected.

    Args:
        base_url: Base URL of webhook receiver

    Returns:
        True if invalid signature is correctly rejected
    """
    print("\nTesting invalid signature rejection...")

    payload = json.dumps({"event": "test"})

    try:
        response = requests.post(
            f"{base_url}/webhook/drupal",
            headers={
                "Content-Type": "application/json",
                "X-Drupal-Signature": "sha256=invalid_signature",
            },
            data=payload,
        )

        if response.status_code == 401:
            print("✓ Invalid signature correctly rejected")
            return True
        else:
            print(f"✗ Expected 401, got {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def main():
    """Run all webhook tests."""
    print("=" * 60)
    print("Drupal Webhook Receiver Test Suite")
    print("=" * 60)

    # Get configuration from environment
    base_url = os.getenv("WEBHOOK_URL", "http://localhost:5000")
    secret = os.getenv("DRUPAL_WEBHOOK_SECRET", "")

    if not secret:
        print("\n⚠️  Warning: DRUPAL_WEBHOOK_SECRET not set")
        print("Using empty secret for testing")
        print("For production, always set a strong secret!\n")

    print(f"Testing webhook receiver at: {base_url}")
    print(f"Secret configured: {bool(secret)}\n")

    # Run tests
    results = []

    results.append(("Health Check", test_health_endpoint(base_url)))

    if secret:
        results.append(
            ("Valid Webhook", test_webhook_payload(base_url, secret, "entity.update"))
        )
        results.append(
            ("Create Event", test_webhook_payload(base_url, secret, "entity.create"))
        )
        results.append(
            ("Delete Event", test_webhook_payload(base_url, secret, "entity.delete"))
        )
        results.append(("Invalid Signature", test_invalid_signature(base_url)))
    else:
        print("\nSkipping signature tests (no secret configured)")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
