podman run -d --name ag-db \
  -e POSTGRES_DB=academicguard \
  -e POSTGRES_USER=academicguard \
  -e POSTGRES_PASSWORD=b53fcee4e923d5b51109fc46 \
  -p 5432:5432 \
  -v ag-db-data:/var/lib/postgresql/data \
  postgres:15-alpine

