import aio_pika, json
from app.core.config import settings
from loguru import logger

_connection = None
_channel    = None

async def get_channel():
    global _connection, _channel
    if not _channel or _channel.is_closed:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        _channel    = await _connection.channel()
    return _channel

async def publish_event(routing_key: str, payload: dict):
    try:
        channel = await get_channel()
        exchange = await channel.declare_exchange("cargo_events", aio_pika.ExchangeType.TOPIC, durable=True)
        await exchange.publish(
            aio_pika.Message(body=json.dumps(payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=routing_key,
        )
        logger.info(f"[MQ] Published {routing_key} → {payload}")
    except Exception as e:
        logger.error(f"[MQ] Publish failed: {e}")