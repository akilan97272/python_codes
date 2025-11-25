from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'hamilton',
    bootstrap_servers=['192.168.0.141:9092'],
    auto_offset_reset='earliest'
)

print("Listening...")

for msg in consumer:
    print("Received:", msg.value.decode('utf-8'))
