import json
import logging

from confluent_kafka import Producer


class KafkaHelper:
    def __init__(self, bootstrap_servers, max_message_bytes=1000*1000, **kwargs):
        """
        Initialize Kafka producer

        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers
            max_message_bytes: Maximum message size in bytes (default 1MB)
            **kwargs: Additional producer configuration
        """
        self.config = {
            'bootstrap.servers': bootstrap_servers,
            'message.max.bytes': max_message_bytes,
            **kwargs
        }
        self.producer = Producer(**self.config)
        self.max_message_bytes = max_message_bytes

    def send_json(self, topic, data, key=None, callback=None):
        """
        Send JSON data to Kafka topic

        Args:
            topic: Target Kafka topic
            data: Data to send (will be JSON serialized)
            key: Optional message key
            callback: Optional delivery callback function

        Returns:
            bool: True if message was queued successfully

        Raises:
            ValueError: If message is too large
            Exception: If JSON serialization fails
        """
        try:
            # Serialize data to JSON bytes
            encoded_data = json.dumps(data, ensure_ascii=False).encode('utf-8')

            # Check message size (leave some buffer for headers)
            max_size = self.max_message_bytes - 50 * 1024
            if len(encoded_data) > max_size:
                raise ValueError(f'Message size {len(encoded_data)} exceeds limit {max_size}')

            # Default callback function
            def default_callback(err, msg):
                if err:
                    logging.error(f'Message delivery failed: {err}')
                else:
                    logging.info(f'Message delivered to {msg.topic()}[{msg.partition()}:{msg.offset()}]')

            delivery_callback = callback or default_callback

            # Send message
            self.producer.produce(
                topic=topic,
                value=encoded_data,
                key=key.encode('utf-8') if key else None,
                callback=delivery_callback
            )

            return True

        except Exception as e:
            logging.error(f'Failed to send message to topic {topic}: {e}')
            raise

    def flush(self, timeout=None):
        """
        Wait for all messages to be delivered

        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
        """
        return self.producer.flush(timeout)

    def close(self):
        """Close the producer"""
        self.producer.flush()


def create_kafka_helper(bootstrap_servers='10.134.11.122:9092,10.134.11.121:9092,10.134.11.120:9092', **kwargs):
    """
    Convenience function to create KafkaHelper with default servers

    Args:
        bootstrap_servers: Kafka broker addresses
        **kwargs: Additional configuration

    Returns:
        KafkaHelper instance
    """
    return KafkaHelper(bootstrap_servers, **kwargs)
