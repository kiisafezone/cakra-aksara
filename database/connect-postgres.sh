#!/data/data/com.termux/files/usr/bin/bash

DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DB_DIR" || return 1

if [ ! -f .venv/bin/activate ]; then
    echo "Virtual environment tidak ditemukan."
    return 1
fi

source .venv/bin/activate

if ! pg_isready -h 127.0.0.1 -p 5432 -q; then
    termux-wake-lock >/dev/null 2>&1 || true
    pg_ctl -D "$PREFIX/var/lib/postgresql" \
        -l "$PREFIX/var/lib/postgresql/server.log" start || return 1

    for i in {1..10}; do
        pg_isready -h 127.0.0.1 -p 5432 -q && break
        sleep 1
    done
fi

if ! pg_isready -h 127.0.0.1 -p 5432 -q; then
    echo "PostgreSQL belum siap."
    return 1
fi

read -r -s -p "Password PostgreSQL uail: " DB_PASS
printf '\n'

if [ -z "$DB_PASS" ]; then
    echo "Password tidak boleh kosong."
    return 1
fi

export DB_PASS

DATABASE_URL="$(python -c '
import os
from sqlalchemy.engine import URL
print(URL.create(
    "postgresql+psycopg",
    username="uail",
    password=os.environ["DB_PASS"],
    host="127.0.0.1",
    port=5432,
    database="uail"
).render_as_string(hide_password=False))
')" || {
    unset DB_PASS
    return 1
}

unset DB_PASS
export DATABASE_URL

echo "PostgreSQL siap digunakan."
echo "Database: uail"
echo "Host: 127.0.0.1"
