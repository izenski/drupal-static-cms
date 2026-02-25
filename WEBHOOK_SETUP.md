# Drupal Webhook Integration Setup

This guide explains how to set up real-time webhook integration between Drupal and your static site generator, eliminating the need for cron-based polling.

## Overview

Instead of periodically checking for changes, Drupal will notify your system immediately when content is created, updated, or deleted. This provides:

- **Instant Updates**: Content appears on your static site within seconds of publishing
- **Reduced Load**: No constant polling of the Drupal API
- **Better Resource Usage**: Only processes content that actually changed
- **Scalability**: Handles high-traffic sites without performance degradation

## Architecture

```
Drupal CMS → Webhook → Flask Receiver → Static Site Generator → S3 Upload
```

## Prerequisites

1. Drupal site with admin access
2. Server to host the webhook receiver (can be same as where main.py runs)
3. Python 3.8+ environment
4. Access to configure webhooks in Drupal

## Part 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask and Gunicorn for the webhook receiver.

## Part 2: Configure Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Required
DRUPAL_BASE_URL=https://your-drupal-site.com
DRUPAL_WEBHOOK_SECRET=your-secret-key-here

# S3 Configuration
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
S3_REGION=us-east-1

# Optional - Webhook Server
WEBHOOK_PORT=5000
FLASK_DEBUG=false
```

### Generating a Webhook Secret

Generate a strong secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use this same secret in both your webhook receiver and Drupal webhook configuration.

## Part 3: Drupal Configuration

### Option A: Using Webhooks Module (Recommended)

1. **Install the Webhooks Module**

   ```bash
   composer require drupal/webhooks
   drush en webhooks -y
   ```

2. **Configure Webhook**
   - Go to **Configuration → Web Services → Webhooks** (`/admin/config/services/webhooks`)
   - Click "Add Webhook"
   - Configure:
     - **Label**: Static Site Generator
     - **URL**: `https://your-server.com/webhook/drupal`
     - **Events**: Select the events to monitor:
       - `entity.create` for node
       - `entity.update` for node
       - `entity.delete` for node
     - **Content Types**: Select which bundles (page, facility, personnel, procedure)
     - **Secret**: Enter the same secret from your `.env` file
     - **Payload Format**: JSON

3. **Webhook Payload Template**

   Configure the webhook to send this JSON structure:

   ```json
   {
     "event": "{{ event }}",
     "entity_type": "{{ entity.getEntityTypeId() }}",
     "bundle": "{{ entity.bundle() }}",
     "entity_id": "{{ entity.id() }}",
     "entity_uuid": "{{ entity.uuid() }}",
     "changed": "{{ entity.changed.value|date('c') }}",
     "title": "{{ entity.label() }}"
   }
   ```

### Option B: Using Custom Module

If you prefer a custom module, create `custom_webhooks/custom_webhooks.module`:

```php
<?php

use Drupal\Core\Entity\EntityInterface;
use GuzzleHttp\Exception\RequestException;

/**
 * Implements hook_entity_update().
 */
function custom_webhooks_entity_update(EntityInterface $entity) {
  _custom_webhooks_notify($entity, 'entity.update');
}

/**
 * Implements hook_entity_insert().
 */
function custom_webhooks_entity_insert(EntityInterface $entity) {
  _custom_webhooks_notify($entity, 'entity.create');
}

/**
 * Implements hook_entity_delete().
 */
function custom_webhooks_entity_delete(EntityInterface $entity) {
  _custom_webhooks_notify($entity, 'entity.delete');
}

/**
 * Send webhook notification.
 */
function _custom_webhooks_notify(EntityInterface $entity, $event) {
  // Only send for nodes
  if ($entity->getEntityTypeId() !== 'node') {
    return;
  }

  // Only for specific content types
  $allowed_bundles = ['page', 'facility', 'personnel', 'procedure'];
  if (!in_array($entity->bundle(), $allowed_bundles)) {
    return;
  }

  $webhook_url = getenv('WEBHOOK_URL');
  $webhook_secret = getenv('WEBHOOK_SECRET');

  if (!$webhook_url) {
    \Drupal::logger('custom_webhooks')->warning('Webhook URL not configured');
    return;
  }

  $payload = [
    'event' => $event,
    'entity_type' => $entity->getEntityTypeId(),
    'bundle' => $entity->bundle(),
    'entity_id' => $entity->id(),
    'entity_uuid' => $entity->uuid(),
    'changed' => $entity->hasField('changed') ? date('c', $entity->changed->value) : date('c'),
    'title' => $entity->label(),
  ];

  $json_payload = json_encode($payload);
  $signature = 'sha256=' . hash_hmac('sha256', $json_payload, $webhook_secret);

  try {
    $client = \Drupal::httpClient();
    $client->post($webhook_url, [
      'headers' => [
        'Content-Type' => 'application/json',
        'X-Drupal-Signature' => $signature,
      ],
      'body' => $json_payload,
      'timeout' => 5,
    ]);
  } catch (RequestException $e) {
    \Drupal::logger('custom_webhooks')->error('Webhook failed: @message', [
      '@message' => $e->getMessage(),
    ]);
  }
}
```

## Part 4: Run the Webhook Receiver

### Development

For testing and development:

```bash
python webhook_receiver.py
```

This starts Flask's development server on port 5000.

### Production

For production, use Gunicorn:

```bash
gunicorn webhook_receiver:app \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### As a Systemd Service

Create `/etc/systemd/system/drupal-webhook.service`:

```ini
[Unit]
Description=Drupal Webhook Receiver
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/drupal-static-cms
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/.env
ExecStart=/path/to/venv/bin/gunicorn webhook_receiver:app \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable drupal-webhook
sudo systemctl start drupal-webhook
sudo systemctl status drupal-webhook
```

### Using Docker

Create `Dockerfile.webhook`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "webhook_receiver:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120"]
```

Run:

```bash
docker build -f Dockerfile.webhook -t drupal-webhook .
docker run -d -p 5000:5000 --env-file .env --name drupal-webhook drupal-webhook
```

## Part 5: Configure Reverse Proxy

### Nginx

```nginx
server {
    listen 80;
    server_name webhooks.yoursite.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

Add SSL with Let's Encrypt:

```bash
sudo certbot --nginx -d webhooks.yoursite.com
```

### Apache

```apache
<VirtualHost *:80>
    ServerName webhooks.yoursite.com

    ProxyPreserveHost On
    ProxyPass / http://localhost:5000/
    ProxyPassReverse / http://localhost:5000/

    ProxyTimeout 120
</VirtualHost>
```

## Testing

### 1. Check Health Endpoint

```bash
curl http://localhost:5000/webhook/health
```

Expected response:

```json
{
  "status": "healthy",
  "timestamp": "2026-02-25T12:00:00.000000",
  "webhook_secret_configured": true
}
```

### 2. Test Webhook Manually

```bash
# Generate signature
PAYLOAD='{"event":"entity.update","entity_type":"node","bundle":"page","entity_uuid":"test-uuid","title":"Test Page"}'
SECRET="your-secret-key"
SIGNATURE="sha256=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)"

# Send request
curl -X POST http://localhost:5000/webhook/drupal \
  -H "Content-Type: application/json" \
  -H "X-Drupal-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

### 3. Test from Drupal

Edit any page in Drupal and save it. Check the webhook receiver logs:

```bash
# If using systemd
sudo journalctl -u drupal-webhook -f

# If running directly
# Watch the console output
```

### 4. Trigger Full Sync

```bash
curl -X POST http://localhost:5000/webhook/trigger-full-sync \
  -H "Content-Type: application/json" \
  -H "X-Drupal-Signature: sha256=$(echo -n '{}' | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)" \
  -d '{}'
```

## Monitoring and Troubleshooting

### Check Logs

The webhook receiver logs all events:

```python
# Logs are in your console or systemd journal
# Shows: incoming requests, validation, processing results
```

### Common Issues

1. **"Invalid signature" error**
   - Ensure the same secret is configured in both Drupal and webhook receiver
   - Check that Drupal is sending the header as `X-Drupal-Signature`

2. **Webhook receiver not accessible**
   - Check firewall rules
   - Verify reverse proxy configuration
   - Ensure webhook receiver is running

3. **Content not updating**
   - Check webhook receiver logs for errors
   - Verify Drupal API credentials are correct
   - Ensure S3 permissions are configured

4. **Timeout errors**
   - Increase Gunicorn timeout: `--timeout 300`
   - Check if S3 uploads are slow
   - Consider async processing for large batches

### Webhook Endpoints

- `POST /webhook/drupal` - Receive Drupal webhook notifications
- `GET /webhook/health` - Health check endpoint
- `POST /webhook/trigger-full-sync` - Manually trigger full site regeneration

## Security Best Practices

1. **Always use HTTPS** in production
2. **Validate webhook signatures** - already implemented
3. **Use strong secrets** - 32+ characters, random
4. **Restrict network access** - firewall rules to only allow Drupal server
5. **Monitor logs** - watch for unusual activity
6. **Rate limiting** - consider adding rate limits to prevent abuse

## Performance Optimization

### For High-Traffic Sites

1. **Use more workers**: `--workers 8` (2-4 × CPU cores)
2. **Enable async processing**: Queue webhooks for background processing
3. **Add Redis**: Cache frequently accessed content
4. **Batch updates**: Group related changes before regenerating

### Example with Celery (Optional)

Install Celery:

```bash
pip install celery redis
```

Modify webhook receiver to queue tasks instead of processing immediately.

## Migrating from Cron

To migrate from cron-based polling to webhooks:

1. Set up webhook receiver and test
2. Configure Drupal webhooks
3. Verify webhooks are working
4. Reduce cron frequency as backup: `0 */6 * * *` (every 6 hours)
5. After 1 week of successful webhook operation, disable cron completely

Keep cron as a fallback for catching any missed webhooks.

## Next Steps

- Add CloudFront cache invalidation after S3 uploads
- Implement content deletion handling
- Add metrics and monitoring (Prometheus, Datadog, etc.)
- Set up alerting for failed webhooks
- Add retry logic for transient failures

## Support

For issues or questions:

- Check webhook receiver logs first
- Verify Drupal webhook configuration
- Test with manual curl commands
- Review this documentation
