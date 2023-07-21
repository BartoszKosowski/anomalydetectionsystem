from configparser import ConfigParser
from argparse import ArgumentParser, FileType
import numpy as np
import tensorflow as tf
from time import sleep
from confluent_kafka import Producer

ANOMALY_RATIO = 0.05

if __name__ == '__main__':
    # Get the producer configuration
    parser = ArgumentParser()
    parser.add_argument('config_file', type=FileType('r'))
    args = parser.parse_args()

    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])

    # Initialize the ECG producer
    producer = Producer(config)

    def delivery_callback(err, msg):
        key = msg.key().decode('utf-8')
        value = msg.value().decode('utf-8')
        if err:
            print(f'ERROR: Message failed delivery: {err}')
        else:
            print(f'Produced event to topic {msg.topic}: key={key} value = {value}')

    # Produce data
    def produce_data():
        anomalous_ecg_generator = tf.keras.models.load_model('../models/generators/anomalous_ecg_generator')
        normal_ecg_generator = tf.keras.models.load_model('../models/generators/normal_ecg_generator')

        sample_id = 0
        try:
            default_sample_duration = np.random.uniform(0.7, 1.1)
            while True:
                sample_duration = np.random.normal(default_sample_duration, 0.1)
                timestamp = sample_duration/140
                if np.random.normal(0.5, 0.5) > ANOMALY_RATIO:
                    sample = normal_ecg_generator.predict(np.random.normal(0, 1, size=(1, 140)))
                    producer.produce(topic='sample_details', key=str(sample_id), value='1')
                    print("True")
                else:
                    sample = anomalous_ecg_generator.predict(np.random.normal(0, 1, size=(1, 140)))
                    producer.produce(topic='sample_details', key=str(sample_id), value='0')
                for i in sample[0]:
                    producer.produce(topic='ecg', key=str(sample_id), value=str(i), callback=delivery_callback)
                    sleep(timestamp)
                sample_id += 1
                producer.poll(10000)
                producer.flush()
        except KeyboardInterrupt:
            pass
        finally:
            print('The stream has been ended')

    produce_data()
