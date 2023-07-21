from datetime import datetime

import numpy as np
import pandas as pd
import tensorflow as tf
from argparse import ArgumentParser, FileType
from configparser import ConfigParser
from confluent_kafka import Consumer, OFFSET_BEGINNING
from sklearn import svm
from sklearn.model_selection import train_test_split
from MongoDbClient import MongoDbClient


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('config_file', type=FileType('r'))
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    config_parser = ConfigParser()
    config_parser.read_file(args.config_file)
    config = dict(config_parser['default'])
    config.update(config_parser['consumer'])

    def prepare_model():
        dataframe = pd.read_csv('../dataset/ecg.csv', header=None)
        raw_data = dataframe.values

        # get last element
        labels = raw_data[:, -1]

        # rest are data
        data = raw_data[:, 0:-1]

        train_data, test_data, train_labels, test_labels = train_test_split(data, labels, test_size=0.2, random_state=21)

        clf = svm.SVC(gamma='auto', decision_function_shape='ovo', class_weight='balanced')
        clf.fit(train_data, train_labels)

        return clf

    # Consumer
    consumer = Consumer(config)
    client = MongoDbClient('svm_recognized_samples')

    # Callback
    def reset_offset(consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)

    consumer.subscribe(topics=['ecg'], on_assign=reset_offset)

    clf = prepare_model()

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
                    result = clf.predict(data)
                    client.insert_record({
                        'sample_id': int(key),
                        'predicted_value': float(result[0][0]),
                        'timestamp': str(datetime.now())
                    })
                    print(result)
                    full_sample = []
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
