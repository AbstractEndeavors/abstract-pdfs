import pika
import json


def publish(queue: str, body: dict, *, host: str = "localhost", port: int = 5672):
    params = pika.ConnectionParameters(host=host, port=port)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(body),
        properties=pika.BasicProperties(delivery_mode=2),  # persistent
    )
    connection.close()


publish("tasks", {"job": "resize_thumbnail", "path": "/imgs/hero.png"})
