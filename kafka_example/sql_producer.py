#sql_producer.py
from confluent_kafka import Producer
import json

conf = {
    "bootstrap.servers": "192.168.0.141:9092"   # your Kafka advertised listener
}

producer = Producer(conf)

def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Delivery failed: {err}")
    else:
        print(f"✔ Message delivered to {msg.topic()} [{msg.partition()}]")

print("Kafka Interactive Producer for topic: hamilton")
print("Press Ctrl+C to exit\n")

while True:
    try:
        # User input
        id_val = int(input("Enter ID (int): "))
        name_val = input("Enter name (string): ")
        value_val = input("Enter value (string): ")

        # Create JSON record
        record = {
            "id": id_val,
            "name": name_val,
            "value": value_val
        }

        json_data = json.dumps(record)

        # Send to Kafka
        producer.produce(
            topic="new_template",
            key=str(id_val),
            value=json_data,
            callback=delivery_report
        )

        # Force message delivery
        producer.poll(0)

        print("Message queued!\n")

    except KeyboardInterrupt:
        print("\nStopping producer...")
        break
    except Exception as e:
        print(f"❌ Error: {e}\n")

producer.flush()
print("All messages sent and producer closed.")
