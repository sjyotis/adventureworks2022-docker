#!/bin/bash
set -e

echo "=========================================="
echo "  AdventureWorks2022 Auto-Restore"
echo "=========================================="

# Determine sqlcmd path (SQL Server 2022 uses tools18)
if [ -f /opt/mssql-tools18/bin/sqlcmd ]; then
    SQLCMD=/opt/mssql-tools18/bin/sqlcmd
elif [ -f /opt/mssql-tools/bin/sqlcmd ]; then
    SQLCMD=/opt/mssql-tools/bin/sqlcmd
else
    echo "ERROR: sqlcmd not found in expected locations!"
    exit 1
fi

# Helper function to run sqlcmd with common args
run_sqlcmd() {
    $SQLCMD -S localhost -U SA -P "$MSSQL_SA_PASSWORD" -C "$@"
}

# Start SQL Server in background
echo "[1/4] Starting SQL Server..."
/opt/mssql/bin/sqlservr &
SQLSERVR_PID=$!

# Wait for SQL Server to be ready
echo "[2/4] Waiting for SQL Server to be ready..."
for i in $(seq 1 90); do
    if run_sqlcmd -Q "SELECT 1" -b -o /dev/null 2>/dev/null; then
        echo "      SQL Server is ready!"
        break
    fi
    if [ $i -eq 90 ]; then
        echo "ERROR: SQL Server failed to start within 3 minutes"
        exit 1
    fi
    echo "      Attempt $i/90..."
    sleep 2
done

# Check if AdventureWorks2022 already exists (persisted from previous run)
echo "[3/4] Checking if AdventureWorks2022 exists..."
DB_COUNT=$(run_sqlcmd -h -1 -Q "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.databases WHERE name = 'AdventureWorks2022'" 2>/dev/null | tr -d '[:space:]')

if [ "$DB_COUNT" = "1" ]; then
    echo "      AdventureWorks2022 already exists. Skipping restore."
else
    echo "      AdventureWorks2022 not found. Proceeding with restore..."

    BACKUP_FILE="/backups/AdventureWorks2022.bak"

    if [ ! -f "$BACKUP_FILE" ]; then
        echo "ERROR: Backup file not found at $BACKUP_FILE"
        echo "Place your AdventureWorks2022.bak file in the ./backups directory"
        exit 1
    fi

    echo "      Reading backup metadata..."
    run_sqlcmd -Q "RESTORE FILELISTONLY FROM DISK = '$BACKUP_FILE'"

    echo "      Restoring database (this may take a minute)..."
    run_sqlcmd -Q \
        "RESTORE DATABASE [AdventureWorks2022]
         FROM DISK = '$BACKUP_FILE'
         WITH
            MOVE 'AdventureWorks2022' TO '/var/opt/mssql/data/AdventureWorks2022.mdf',
            MOVE 'AdventureWorks2022_log' TO '/var/opt/mssql/data/AdventureWorks2022_log.ldf',
            RECOVERY, REPLACE, STATS = 10"

    echo "      Verifying restore..."
    run_sqlcmd -Q \
        "SELECT name, state_desc, recovery_model_desc FROM sys.databases WHERE name = 'AdventureWorks2022'"

    echo "      Restore completed successfully!"
fi

echo "[4/4] SQL Server is running and ready!"
echo "=========================================="
echo "  Host: localhost:${MSSQL_PORT:-1433}"
echo "  Database: AdventureWorks2022"
echo "  User: sa"
echo "  Password: [see .env file]"
echo "=========================================="

# Bring SQL Server to foreground (keeps container alive)
wait $SQLSERVR_PID
EOF
