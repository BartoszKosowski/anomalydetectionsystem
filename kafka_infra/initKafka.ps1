docker compose up -d

docker compose exec broker `
kafka-topics --create --topic ecg --bootstrap-server localhost:9092 --replication-factor 1 --partitions 2

docker compose exec broker `
kafka-topics --create --topic sample_details --bootstrap-server localhost:9092 --replication-factor 1 --partitions 2
