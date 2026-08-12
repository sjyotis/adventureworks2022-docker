# 🐳 AdventureWorks SQL Server with DBeaver Keystore Helper

A complete local development environment for **Microsoft SQL Server 2022** running in Docker, pre-loaded with the **AdventureWorks2022** sample database. Also includes a tiny utility to generate a dummy Java keystore – useful when DBeaver complains about missing keystore parameters.

---

## 🧰 What's inside

- **SQL Server 2022** container (official Microsoft image)
- Automatic restore of `AdventureWorks2022.bak` on first start
- Healthcheck & graceful shutdown
- **Keystore generator** – a Python script + Docker Compose that creates a dummy `dummy.jks` file
- Connection details for DBeaver (or any SQL client)

---

## 📦 Prerequisites

- Docker & Docker Compose (or Docker Desktop with Compose V2)
- Python 3.6+ (only if you use the keystore generator script)
- A copy of `AdventureWorks2022.bak` placed in the `./backups/` directory

---

## 🚀 Getting Started

### 1. Clone / create project structure

```
.
├── docker-compose.yml          # main database service
├── .env                        # environment variables (SA_PASSWORD, etc.)
├── backups/
│   └── AdventureWorks2022.bak  # your backup file
├── init/
│   └── entrypoint.sh           # restore script (must be executable)
└── keystore-generator/         # optional helper
    ├── docker-compose.yml
    └── generate_keystore.py
```

### 2. Configure environment

Create a `.env` file:

```env
SA_PASSWORD=YourStrong!Password123
MSSQL_PORT=1433
MSSQL_PID=Developer
```

> ⚠️ Use a strong password (at least 8 characters, mix of upper/lower/digits/symbols).

### 3. Make the entrypoint script executable

```bash
chmod +x ./init/entrypoint.sh
```

### 4. Start the database

```bash
docker compose up -d
```

Watch the logs:

```bash
docker compose logs -f
```

You should see the database start and the restore process run automatically. The container will stay healthy and ready.

---

## 🔑 Keystore Generator (for DBeaver)

If you see this error in DBeaver:

```
"keyStoreAuthentication" connection string keyword must be specified, if "keyStoreSecret" is specified.
```

…and you **can't remove** the `keyStoreSecret` parameter, you need a dummy keystore.

The generator creates one for you in seconds.

### Option A – Use the Python script

```bash
cd keystore-generator
python3 generate_keystore.py
```

It will:
- Check Docker
- Spin up a lightweight container with `eclipse-temurin:11-jre-alpine`
- Run `keytool` to create `dummy.jks` in the current folder
- Print the exact DBeaver property values
- Remove the container automatically

### Option B – Run Docker directly

```bash
docker run --rm -v $(pwd):/output eclipse-temurin:11-jre-alpine \
  sh -c "keytool -genkey -alias dummy -keyalg RSA -keysize 2048 \
  -keystore /output/dummy.jks -storepass dummy123 -keypass dummy123 \
  -dname 'CN=dummy' && chmod 644 /output/dummy.jks"
```

The keystore file `dummy.jks` will appear in your current directory.

---

## 🔌 Connecting with DBeaver

1. Create a new **SQL Server** connection
2. Fill in:
   - **Host**: `localhost` (or your server IP)
   - **Port**: `1433` (or the one you set)
   - **Authentication**: SQL Server Authentication
   - **Username**: `sa`
   - **Password**: `YourStrong!Password123`
3. Go to the **Driver properties** tab and add:

| Property                 | Value                              |
|--------------------------|------------------------------------|
| `keyStoreAuthentication` | `JavaKeyStorePassword`             |
| `keyStoreLocation`       | `/full/path/to/dummy.jks`          |
| `keyStoreSecret`         | `dummy123`                         |
| `TrustServerCertificate` | `true`                             |

> The `TrustServerCertificate=true` is often needed for Docker-based SQL Server instances without proper SSL.

4. Test the connection – you should be in.

---

## 🧹 Cleaning Up

To stop and remove the database container and volumes:

```bash
docker compose down -v
```

The keystore generator leaves no containers behind – it's fully self-cleaning.

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| `entrypoint.sh: Permission denied` | Run `chmod +x ./init/entrypoint.sh` on the host. |
| Keystore image not found | The generator uses `eclipse-temurin:11-jre-alpine` – it's actively maintained. |
| DB not starting / password policy | Ensure `SA_PASSWORD` meets SQL Server's complexity rules. |
| Can't connect from host | Check firewall and port mapping. Use `TrustServerCertificate=true`. |

---

## 📄 License

This project is provided as-is for development and testing purposes. AdventureWorks is a Microsoft sample database – use it freely.

---

## 🙌 Credits

- Microsoft for SQL Server and AdventureWorks
- Eclipse Temurin for the Java runtime
- Docker for making containerisation easy

---

**Happy querying!** 🐘📊

