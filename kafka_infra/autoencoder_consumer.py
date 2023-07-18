import numpy as np
import pandas as pd
import tensorflow as tf
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, OFFSET_BEGINNING

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

    # Callback
    def reset_offset(consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)

    consumer.subscribe(topics=['ecg'], on_assign=reset_offset)

    autoencoder_model = tf.keras.models.load_model('../models/detectors/ann')

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
                if len(full_sample) < 140:
                    full_sample.append(float(value))
                else:
                    df = pd.DataFrame(full_sample)
                    data = np.transpose(df.values)
                    result = autoencoder_model.predict(data)
                    print(result)
                    full_sample = []
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
