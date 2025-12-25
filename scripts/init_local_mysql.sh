#!/usr/bin/env bash
set -euo pipefail

# init_local_mysql.sh
# Convenience script to create the development database and user for local MySQL.
# Usage:
#   ./scripts/init_local_mysql.sh [--root-pw PASSWORD] [--user NAME] [--password PW] [--db NAME] [--host HOST] [--port PORT]
# Environment variables may also be used (MYSQL_ROOT_PW, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_HOST, MYSQL_PORT).

print_usage() {
  cat <<'USAGE'
Usage: init_local_mysql.sh [options]

Options:
  --root-pw PASSWORD    Root password (can also set MYSQL_ROOT_PW env var)
  --user NAME           Dev username (default: plan) or MYSQL_USER
  --password PW         Dev user password (default: changeme) or MYSQL_PASSWORD
  --db NAME             Database name (default: plan_db) or MYSQL_DB
  --host HOST           MySQL host (default: 127.0.0.1) or MYSQL_HOST
  --port PORT           MySQL port (default: 3306) or MYSQL_PORT
  -h, --help            Show this help message

Example:
  ./scripts/init_local_mysql.sh --root-pw myrootpw --user plan --password changeme --db plan_db
USAGE
}

# defaults from env
MYSQL_ROOT_USER=${MYSQL_ROOT_USER:-root}
MYSQL_ROOT_PW=${MYSQL_ROOT_PW:-}
MYSQL_USER=${MYSQL_USER:-plan}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-changeme}
MYSQL_DB=${MYSQL_DB:-plan_db}
MYSQL_HOST=${MYSQL_HOST:-127.0.0.1}
MYSQL_PORT=${MYSQL_PORT:-3306}

# simple arg parse
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --root-pw)
      MYSQL_ROOT_PW="$2"; shift 2;;
    --user)
      MYSQL_USER="$2"; shift 2;;
    --password)
      MYSQL_PASSWORD="$2"; shift 2;;
    --db)
      MYSQL_DB="$2"; shift 2;;
    --host)
      MYSQL_HOST="$2"; shift 2;;
    --port)
      MYSQL_PORT="$2"; shift 2;;
    -h|--help)
      print_usage; exit 0;;
    *)
      echo "Unknown argument: $1"; print_usage; exit 1;;
  esac
done

# ensure mysql client is available
if ! command -v mysql >/dev/null 2>&1; then
  echo "Error: mysql client not found. Install MySQL client before running this script." >&2
  exit 2
fi

run_mysql() {
  if [ -n "${MYSQL_ROOT_PW}" ]; then
    mysql -u "${MYSQL_ROOT_USER}" -p"${MYSQL_ROOT_PW}" -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -e "$1"
  else
    mysql -u "${MYSQL_ROOT_USER}" -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -e "$1"
  fi
}

echo "Connecting to MySQL ${MYSQL_HOST}:${MYSQL_PORT} as ${MYSQL_ROOT_USER}"

SQL_CMD="CREATE DATABASE IF NOT EXISTS \`$MYSQL_DB\`;"
if ! run_mysql "$SQL_CMD"; then
  echo "Error: Could not create database. Please check root credentials or run the SQL manually." >&2
  exit 3
fi

SQL_CMD="CREATE USER IF NOT EXISTS '$MYSQL_USER'@'localhost' IDENTIFIED WITH mysql_native_password BY '$MYSQL_PASSWORD';"
run_mysql "$SQL_CMD"

SQL_CMD="GRANT ALL PRIVILEGES ON \`$MYSQL_DB\`.* TO '$MYSQL_USER'@'localhost';"
run_mysql "$SQL_CMD"

run_mysql "FLUSH PRIVILEGES;"

echo "Done. Update your .env or environment variables and run the app. Example .env values:"
echo "  MYSQL_HOST=$MYSQL_HOST"
echo "  MYSQL_PORT=$MYSQL_PORT"
echo "  MYSQL_DB=$MYSQL_DB"
echo "  MYSQL_USER=$MYSQL_USER"
echo "  MYSQL_PASSWORD=$MYSQL_PASSWORD"

echo "You can now run: python3 scripts/seed_scheduler.py"