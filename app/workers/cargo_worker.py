import asyncio, aio_pika, json
from loguru import logger
from app.core.config import settings

MAX_RETRIES = 3

async def handle_message(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        body = json.loads(message.body)
        retries = int(message.headers.get("x-retries", 0))
        try:
            logger.info(f"[WORKER] Processing cargo event: {body}")
            # ── your business logic here ──
            # e.g. update external tracking API, send SMS, etc.
        except Exception as e:
            logger.error(f"[WORKER] Error: {e} | retry {retries}/{MAX_RETRIES}")
            if retries < MAX_RETRIES:
                await asyncio.sleep(2 ** retries)   # exponential backoff
                await message.channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message.body,
                        headers={"x-retries": retries + 1},
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=message.routing_key,
                )
            else:
                logger.warning(f"[DLQ] Message moved to dead-letter: {body}")

async def start_worker():
    conn     = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel  = await conn.channel()
    exchange = await channel.declare_exchange("cargo_events", aio_pika.ExchangeType.TOPIC, durable=True)
    queue    = await channel.declare_queue("cargo.jobs", durable=True)
    dlq      = await channel.declare_queue("cargo.dlq",  durable=True)
    await queue.bind(exchange, routing_key="cargo.*")
    await queue.consume(handle_message)
    logger.info("[WORKER] Cargo worker running...")
    await asyncio.Future()   # run forever

if __name__ == "__main__":
    asyncio.run(start_worker())