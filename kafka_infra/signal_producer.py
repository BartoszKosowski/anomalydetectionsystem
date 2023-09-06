from configparser import ConfigParser
from argparse import ArgumentParser, FileType
import numpy as np
from confluent_kafka import Producer

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

    def generate_signal_with_anomalies(freq, num_samples, max_anomalies, max_freq, force_normal=False):
        sample_rate = 2 * max_freq
        length = num_samples / sample_rate

        t = np.linspace(0, length, num_samples)
        signal = np.sin(2 * np.pi * freq * t)

        if not force_normal:
        # Losowo zdecyduj o liczbie anomalii
            num_anomalies = np.random.randint(0, max_anomalies + 1)

        # Wprowadź anomalie
            for _ in range(num_anomalies):
                anomaly_start = np.random.randint(0, len(t) //2 )  # Zmiana tutaj
                anomaly_end = min(anomaly_start + np.random.randint(sample_rate // 2, sample_rate), len(t)-1)  # i tutaj
                anomaly_type = np.random.choice(['amp', 'freq', 'noise'])

                if anomaly_type == 'amp':
                    signal[anomaly_start:anomaly_end] *= 1.5
                elif anomaly_type == 'freq':
                    signal[anomaly_start:anomaly_end] = np.sin(2 * np.pi * (freq*1.5) * t[anomaly_start:anomaly_end])
                elif anomaly_type == 'noise':
                    signal[anomaly_start:anomaly_end] += np.random.normal(0, 0.5, anomaly_end - anomaly_start)

        return signal

    def prepare_data():
        all_samples_count = 1400
        anomaly_ratio = np.arange(0.10,0.15,0.01)
        normal_samples_count = int(all_samples_count * (1 - np.random.choice(anomaly_ratio)))
        anomalous_samples_count = int(all_samples_count - normal_samples_count)
        freq = 100
        sample_length = 100
        max_freq = 100
        dataset = []

        for _ in range(0,normal_samples_count):
            signal = generate_signal_with_anomalies(freq, sample_length, 3, max_freq, force_normal=True)
            dataset.append(np.append(signal, 1))

        for _ in range(0,anomalous_samples_count):
            signal = generate_signal_with_anomalies(freq, sample_length, 3, max_freq, force_normal=False)
            dataset.append(np.append(signal, 0))

        np.random.shuffle(dataset)
        return np.array(dataset)

    def delivery_callback(err, msg):
        key = msg.key().decode('utf-8')
        value = msg.value().decode('utf-8')
        if err:
            print(f'ERROR: Message failed delivery: {err}')
        else:
            print(f'Produced event to topic {msg.topic}: key={key} value = {value}')

    # Produce data
    def produce_data():
        dataset = prepare_data()
        labels = dataset[:,-1]
        data = dataset[:, 0:-1]
        sample_id = 0
        try:
            for i in range(0,len(dataset)):
                if labels[i] == 1:
                    label = '1'
                else:
                    label = '0'
                producer.produce(topic='sample_details', key=str(sample_id), value=label.encode('utf-8'))

                for j in data[i]:
                    producer.produce(topic='ecg', key=str(sample_id), value=str(j).encode('utf-8'), callback=delivery_callback)
                    # sleep(timestamp)
                sample_id += 1
                producer.poll(10000)
                producer.flush()
        except KeyboardInterrupt:
            pass
        finally:
            print('The stream has been ended')

    produce_data()
