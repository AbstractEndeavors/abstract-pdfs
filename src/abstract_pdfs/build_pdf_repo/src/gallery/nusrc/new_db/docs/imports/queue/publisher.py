# publisher.py
import pika
import json


def publish_all(queue: str, pdf_paths: list[str], *, host: str = "localhost"):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)

    for pdf_path in pdf_paths:
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps({"pdf_path": pdf_path}),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        print(f"queued: {pdf_path}")

    connection.close()


# usage
publish_all("pdf_slicing", all_pdfs)
