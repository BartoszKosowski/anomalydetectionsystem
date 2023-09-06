import numpy as np
import pandas as pd
import tensorflow as tf
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, OFFSET_BEGINNING
from MongoDbClient import MongoDbClient
from datetime import datetime

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('config_file', type=FileType('r'))
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])
    config.update(config_parser['consumer'])

    # Consumer
    consumer = Consumer(config)
    client = MongoDbClient('ann_recognized_samples_signal')

    # Callback
    def reset_offset(consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)

    consumer.subscribe(topics=['ecg'], on_assign=reset_offset)

    ann_model = tf.keras.models.load_model('../models/detectors/ann_signal')

    try:
        full_sample = []
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                full_sample = []
                print('Waiting for data...')
            elif msg.error():
                full_sample = []
                print(f'ERROR: {msg.error()}')
            else:
                key = msg.key().decode('utf-8')
                value = msg.value().decode('utf-8')
                if len(full_sample) < 100:
                    full_sample.append(float(value))
                else:
                    start_time = datetime.now()
                    df = pd.DataFrame(full_sample)
                    data = np.transpose(df.values)
                    result = ann_model.predict(data)
                    duration = int((datetime.now() - start_time).total_seconds()*1000)
                    client.insert_record({
                        'sample_id': int(key)-1,
                        'predicted_value': float(result[0][0]),
                        'duration': duration,
                        'timestamp': str(datetime.now())
                    })
                    full_sample = []
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
