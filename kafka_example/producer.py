from confluent_kafka import Producer

BOOTSTRAP_SERVERS = "192.168.0.141:9092"
TOPIC = "hamilton"


def main():
    conf = {"bootstrap.servers": BOOTSTRAP_SERVERS}
    producer = Producer(conf)

    print("\n=== Manual Kafka Producer (TEXT MODE) ===")
    print("Type a message and press Enter to send.")
    print("Type 'exit' to quit.\n")

    while True:
        user_msg = input("Enter message: ")

        if user_msg.lower() == "exit":
            break

        # send raw text WITHOUT delivery callback
        producer.produce(
            TOPIC,
            value=user_msg.encode("utf-8")
        )
        producer.poll(0)

        print(f"[PRODUCER] Sent: {user_msg}")

    print("\n[PRODUCER] Flushing pending messages…")
    producer.flush()
    print("[PRODUCER] Closed.\n")


if __name__ == "__main__":
    main()