
.PHONY: migrate seed

migrate:
	kubectl port-forward -n mysql service/mysql 3306:3306 & \
	sleep 3 && cd src && \
	DATABASE_URL="$$(cd ../terraform && terraform output --raw database_url | sed 's/mysql.mysql.svc.cluster.local/127.0.0.1/g')" \
	poetry run prisma db push

seed:
	kubectl port-forward -n mysql service/mysql 3306:3306 & \
	sleep 3 && cd src && \
	DATABASE_URL="$$(cd ../terraform && terraform output --raw database_url | sed 's/mysql.mysql.svc.cluster.local/127.0.0.1/g')" \
	poetry run python ../scripts/seed.py

