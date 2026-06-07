import asyncio
import aio_pika
async def t():
    conn = await aio_pika.connect_robust("amqp://cargoapp:cargoapp@127.0.0.1:5672/")
    print("CONNECTED OK")
    await conn.close()
asyncio.run(t())
