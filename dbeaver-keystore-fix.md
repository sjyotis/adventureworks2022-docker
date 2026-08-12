# DBeaver Keystore Fix for SQL Server

If DBeaver keeps throwing errors about `keyStoreAuthentication`, `keyStoreSecret`, or certificate validation when connecting to a local SQL Server Docker container, this is why: the Microsoft JDBC driver that DBeaver uses has Azure Key Vault support baked in, and sometimes it leaks into local connections. Even when you clear the properties, they can come back from driver-level defaults or stale connection templates.

Instead of fighting DBeaver's settings for an hour, you can create a dummy Java keystore (JKS) file and point DBeaver at it. The driver sees a valid keystore, validates successfully, and gets out of your way.

This is a workaround, not a proper security setup. It's fine for a local dev container. Don't use this for production or internet-facing databases.

---

## What You Need

- Docker (to run the `keytool` command in a container)
- A few seconds of patience

---

## Quick Setup

### 1. Create the Keystore

You can do this with a one-liner using a Java container:

```bash
docker run --rm -v "$(pwd):/output" eclipse-temurin:11-jre-alpine   keytool -genkey -alias dummy -keyalg RSA -keysize 2048   -keystore /output/dummy.jks   -storepass dummy123 -keypass dummy123   -dname 'CN=dummy'
```

This creates `dummy.jks` in your current directory with:
- Keystore password: `dummy123`
- Alias: `dummy`
- A self-signed RSA keypair

### 2. Set the Permissions

Make sure your user can read it:

```bash
chmod 644 dummy.jks
```

### 3. Configure DBeaver

Open your SQL Server connection in DBeaver and go to the **Driver Properties** tab. Set these four properties:

| Property | Value |
|----------|-------|
| `keyStoreAuthentication` | `JavaKeyStorePassword` |
| `keyStoreLocation` | `/absolute/path/to/your/dummy.jks` |
| `keyStoreSecret` | `dummy123` |
| `trustServerCertificate` | `true` |

**Important:** Use the **absolute path** for `keyStoreLocation`. DBeaver doesn't resolve `~` or relative paths reliably here.

Example:
```
keyStoreLocation = /home/yourname/projects/adventureworks/dummy.jks
```

### 4. Test the Connection

Click **Test Connection** in DBeaver. It should connect without certificate errors.

---

## The Docker Compose Way (Optional)

If you want a repeatable setup, here's a `docker-compose.yml` that generates the keystore and prints the connection details:

```yaml
services:
  keystore-generator:
    image: eclipse-temurin:11-jre-alpine
    container_name: keystore-generator
    volumes:
      - ./:/output
    entrypoint: >
      sh -c "
        keytool -genkey -alias dummy -keyalg RSA -keysize 2048
          -keystore /output/dummy.jks
          -storepass dummy123 -keypass dummy123
          -dname 'CN=dummy' &&
        chmod 644 /output/dummy.jks &&
        echo 'Keystore created at '$(pwd)/dummy.jks
      "
```

Run it:

```bash
docker compose -f docker-compose.keystore.yml up
```

Then use the `dummy.jks` file it creates.

---

## Why This Happens

DBeaver uses the Microsoft JDBC Driver for SQL Server. Recent versions of this driver include Azure Active Directory and Azure Key Vault authentication features. When DBeaver's driver properties get into a weird state — either from a previous connection, a global driver default, or an auto-updated driver — it can start requiring keystore fields even for basic SQL Server Authentication.

The error usually looks like one of these:

- `"keyStoreAuthentication" connection string keyword must be specified, if "keyStoreSecret" is specified`
- `PKIX path building failed: unable to find valid certification path to requested target`
- `The driver could not establish a secure connection to SQL Server`

Clearing the properties in one connection window doesn't always fix it because the driver itself might have cached defaults. Creating a dummy keystore satisfies the validation check and lets you move on with your life.

---

## The "Nuclear Option" (If You Want to Actually Fix DBeaver)

If you don't want to use a dummy keystore, you can try resetting DBeaver's driver completely:

1. **Window → Preferences → Connections → Drivers → Microsoft JDBC Driver for SQL Server**
2. Click **Reset to Defaults** (or delete the driver and let DBeaver re-download it)
3. In your connection: **Driver Properties → gear icon → Reset to Defaults**
4. Add back only: `trustServerCertificate = true`

Sometimes this works. Sometimes the properties come back anyway. The dummy keystore is faster and more reliable.

---

## Cleanup

The `dummy.jks` file is just a small binary file (a couple KB). It contains a fake self-signed certificate. You can delete it anytime without breaking anything — just remember to remove the driver properties from DBeaver too, or the connection will fail looking for the missing file.

---

## Summary

| What | Value |
|------|-------|
| Keystore file | `dummy.jks` |
| Password | `dummy123` |
| DBeaver property `keyStoreAuthentication` | `JavaKeyStorePassword` |
| DBeaver property `keyStoreLocation` | absolute path to `dummy.jks` |
| DBeaver property `keyStoreSecret` | `dummy123` |
| DBeaver property `trustServerCertificate` | `true` |

This gets DBeaver talking to your local Docker SQL Server without the certificate drama.
