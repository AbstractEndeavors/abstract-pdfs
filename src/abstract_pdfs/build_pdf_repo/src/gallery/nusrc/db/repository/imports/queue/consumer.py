# consumer.py
import pika
import json


def handle_task(ch, method, properties, body):
    msg = json.loads(body)
    pdf_path = msg["pdf_path"]

    try:
        print(f"slicing: {pdf_path}")
        slice_pdf(pdf_path)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"failed on {pdf_path}: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def consume(queue: str, *, host: str = "localhost"):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue, on_message_callback=handle_task)

    print(f"waiting on '{queue}'...")
    channel.start_consuming()


consume("pdf_slicing")
