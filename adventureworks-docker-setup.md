# AdventureWorks2022 on Docker — The Real Setup

This is a working Docker Compose setup that restores Microsoft's AdventureWorks2022 sample database into SQL Server 2022 automatically. No manual restore commands, no copy-pasting into SSMS. You run `docker compose up -d` and it handles everything.

I built this because I got tired of doing the same dance every time: start SQL Server, wait for it to be ready, figure out the logical file names from the backup, run the restore, then fight DBeaver for 20 minutes because it doesn't trust the self-signed certificate. This does it all in one shot.

---

## What You Need

- Docker and Docker Compose
- The `AdventureWorks2022.bak` file from Microsoft
- About 2GB of free RAM for the container
- Port 1433 free (or change it in `.env`)

---

## File Layout

```
adventureworks/
├── .env
├── docker-compose.yml
├── init/
│   └── entrypoint.sh
└── backups/
    └── AdventureWorks2022.bak   <-- put it here
```

---

## The Files

### `.env`

```bash
SA_PASSWORD=YourStrong@Passw0rd
MSSQL_PID=Developer
MSSQL_PORT=1433
```

The password needs to be strong — SQL Server won't start with `password123`. Mix of upper, lower, number, symbol, 8+ chars.

### `docker-compose.yml`

```yaml
services:
  mssql:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: adventureworks-mssql
    hostname: adventureworks-mssql
    user: root
    env_file:
      - .env
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: ${SA_PASSWORD}
      MSSQL_PID: ${MSSQL_PID:-Developer}
      MSSQL_BACKUP_DIR: /var/opt/mssql/backups
      MSSQL_DATA_DIR: /var/opt/mssql/data
      MSSQL_LOG_DIR: /var/opt/mssql/log
    ports:
      - "${MSSQL_PORT:-1433}:1433"
    volumes:
      - mssql_data:/var/opt/mssql/data
      - mssql_log:/var/opt/mssql/log
      - mssql_backups:/var/opt/mssql/backups
      - ./backups:/backups:ro
      - ./init/entrypoint.sh:/usr/config/entrypoint.sh:ro
    entrypoint: ["/bin/bash", "/usr/config/entrypoint.sh"]
    healthcheck:
      test:
        - "CMD"
        - "/opt/mssql-tools18/bin/sqlcmd"
        - "-S"
        - "localhost"
        - "-U"
        - "sa"
        - "-P"
        - "${SA_PASSWORD}"
        - "-C"
        - "-Q"
        - "SELECT 1"
        - "-b"
        - "-o"
        - "/dev/null"
      interval: 15s
      timeout: 5s
      retries: 12
      start_period: 60s
    restart: unless-stopped
    networks:
      - mssql_net
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

volumes:
  mssql_data:
    driver: local
  mssql_log:
    driver: local
  mssql_backups:
    driver: local

networks:
  mssql_net:
    driver: bridge
```

Notes on the choices here:

- `user: root` — SQL Server's default `mssql` user sometimes can't write to Docker volumes depending on your host filesystem. Running as root avoids permission headaches. This is fine for local dev, don't do it in production.
- `entrypoint` runs through `/bin/bash` because if you're storing this on a cloud-synced drive (like Koofr, Dropbox, etc.), executable permissions get stripped. Running it through bash means you don't need the execute bit.
- The healthcheck uses `-C` because `sqlcmd` v18 (bundled with SQL Server 2022) refuses to connect to localhost without trusting the self-signed cert, even though it's the same machine.

### `init/entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "  AdventureWorks2022 Auto-Restore"
echo "=========================================="

# Find sqlcmd — SQL Server 2022 moved it to tools18
if [ -f /opt/mssql-tools18/bin/sqlcmd ]; then
    SQLCMD=/opt/mssql-tools18/bin/sqlcmd
elif [ -f /opt/mssql-tools/bin/sqlcmd ]; then
    SQLCMD=/opt/mssql-tools/bin/sqlcmd
else
    echo "ERROR: sqlcmd not found"
    exit 1
fi

# Helper to avoid typing the same args every time
run_sqlcmd() {
    $SQLCMD -S localhost -U SA -P "$MSSQL_SA_PASSWORD" -C "$@"
}

# Start SQL Server in the background
echo "[1/4] Starting SQL Server..."
/opt/mssql/bin/sqlservr &
SQLSERVR_PID=$!

# Wait until SQL Server actually accepts connections
# This can take 30-60 seconds on first boot
echo "[2/4] Waiting for SQL Server to be ready..."
for i in $(seq 1 90); do
    if run_sqlcmd -Q "SELECT 1" -b -o /dev/null 2>/dev/null; then
        echo "      Ready!"
        break
    fi
    if [ $i -eq 90 ]; then
        echo "ERROR: Timed out waiting for SQL Server"
        exit 1
    fi
    echo "      Attempt $i/90..."
    sleep 2
done

# Check if we already restored this database in a previous run
# The data is persisted in the named volume, so we don't want to restore again
echo "[3/4] Checking if AdventureWorks2022 exists..."
DB_COUNT=$(run_sqlcmd -h -1 -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.databases WHERE name = 'AdventureWorks2022'" 2>/dev/null | tr -d '[:space:]')

if [ "$DB_COUNT" = "1" ]; then
    echo "      Already exists. Skipping restore."
else
    echo "      Not found. Starting restore..."

    BACKUP_FILE="/backups/AdventureWorks2022.bak"

    if [ ! -f "$BACKUP_FILE" ]; then
        echo "ERROR: $BACKUP_FILE not found"
        echo "Make sure AdventureWorks2022.bak is in the ./backups folder"
        exit 1
    fi

    echo "      Reading backup file list..."
    run_sqlcmd -Q "RESTORE FILELISTONLY FROM DISK = '$BACKUP_FILE'"

    echo "      Restoring (this takes a minute)..."
    run_sqlcmd -Q "RESTORE DATABASE [AdventureWorks2022] FROM DISK = '$BACKUP_FILE' WITH MOVE 'AdventureWorks2022' TO '/var/opt/mssql/data/AdventureWorks2022.mdf', MOVE 'AdventureWorks2022_log' TO '/var/opt/mssql/data/AdventureWorks2022_log.ldf', RECOVERY, REPLACE, STATS = 10"

    echo "      Verifying..."
    run_sqlcmd -Q "SELECT name, state_desc FROM sys.databases WHERE name = 'AdventureWorks2022'"

    echo "      Done!"
fi

echo "[4/4] SQL Server is running."
echo "=========================================="
echo "  Host:     localhost:${MSSQL_PORT:-1433}"
echo "  Database: AdventureWorks2022"
echo "  User:     sa"
echo "=========================================="

# Keep the container alive by waiting for the background process
wait $SQLSERVR_PID
```

What the script does, step by step:

1. **Finds sqlcmd** — SQL Server 2022 ships it in `tools18`, older versions use `tools`. The script checks both.
2. **Starts SQL Server** in the background with `sqlservr &`
3. **Polls every 2 seconds** until `SELECT 1` succeeds. First boot is slow because SQL Server copies system databases (`master`, `model`, `msdb`) from template files.
4. **Checks for existing database** — If you stop and restart the container, the data volume keeps the database alive, so it skips the restore.
5. **Restores the backup** — Uses `RESTORE FILELISTONLY` first to show you what's inside the `.bak`, then `RESTORE DATABASE ... WITH MOVE` to place the `.mdf` and `.ldf` files in the right data directory.
6. **Waits forever** — `wait $SQLSERVR_PID` keeps the container running until you stop it.

---

## How to Use It

### First Time

```bash
# 1. Put the backup in the right place
mv AdventureWorks2022.bak backups/

# 2. Make sure the script is readable (execute bit not needed since we run through bash)
chmod +x init/entrypoint.sh   # optional, but harmless

# 3. Start it
docker compose up -d

# 4. Watch the logs
docker compose logs -f
```

You'll see SQL Server boot up, upgrade system databases, then the script kicks in and restores AdventureWorks. Once you see `Restore completed successfully!`, you're good.

### Connect with DBeaver

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `1433` (or your `.env` value) |
| Database | `AdventureWorks2022` |
| Auth | SQL Server Authentication |
| User | `sa` |
| Password | whatever you set in `.env` |

**Driver Properties tab:**
- `trustServerCertificate` → `true`

If DBeaver still throws certificate or keystore errors, see the companion guide: `dbeaver-keystore-fix.md`.

### Day-to-Day Commands

```bash
# Stop (keeps data)
docker compose down

# Start again (skips restore, uses existing DB)
docker compose up -d

# Wipe everything including the database (irreversible)
docker compose down -v

# Shell into the container
docker exec -it adventureworks-mssql bash

# Run a query manually
docker exec -it adventureworks-mssql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P 'YourStrong@Passw0rd' -C -Q "SELECT TOP 5 * FROM AdventureWorks2022.Person.Person"
```

---

## Problems You Might Hit

### "Permission denied" on entrypoint.sh

If you see `/bin/bash: /usr/config/entrypoint.sh: Permission denied`, it means the file lost its execute bit — common on cloud-synced folders. We already fixed this by running it through `/bin/bash` in the compose file, but if you ever switch back to running it directly, just make sure the mount point works.

### "Access is denied" on master.mdf

SQL Server's default `mssql` user can't write to the volume. That's why we added `user: root`. If you remove that line and hit this error on a standard Linux filesystem, the volume permissions are wrong. `user: root` is the quickest fix for local dev.

### Restore fails with "logical file name not found"

Your `.bak` might use different internal names than `AdventureWorks2022` and `AdventureWorks2022_log`. Check with:

```bash
docker exec -it adventureworks-mssql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '...' -C -Q "RESTORE FILELISTONLY FROM DISK = '/backups/AdventureWorks2022.bak'"
```

Then edit the `MOVE` lines in `entrypoint.sh` to match.

### DBeaver says "Cannot open database"

Either the restore hasn't finished yet (check logs), or DBeaver is trying to connect to `master` instead of `AdventureWorks2022`. Make sure the Database field in your connection is filled in.

### Port 1433 already in use

Change `MSSQL_PORT` in `.env` to something else, like `1434`.

---

## Why This Is More Than Just "Docker Run SQL Server"

Most tutorials stop at `docker run mcr.microsoft.com/mssql/server`. This setup handles the boring parts:

- **Automated restore on first boot** — no manual `RESTORE DATABASE` commands
- **Idempotency** — won't try to restore over an existing database on restart
- **Certificate trust** — `sqlcmd` v18 is strict about SSL; the `-C` flag handles it
- **Permission edge cases** — works even on cloud-synced drives that strip Unix permissions
- **Persistent data** — named volumes keep your database between restarts

It's a complete local dev environment, not a one-liner.
