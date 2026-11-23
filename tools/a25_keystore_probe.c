/*
 * Minimal, read-only Keystore2 database probe.
 *
 * Usage:
 *   a25_keystore_probe --self-test
 *   a25_keystore_probe DATABASE_A DATABASE_B
 *
 * The two reported counts are deliberately aggregate-only: no alias or key
 * material is ever printed.  The database schema used by Keystore2 stores
 * aliases in keyentry(domain, namespace, alias).
 *
 * immutable=1 does not lock the database. Only use this against a database
 * proven quiescent for the whole inspection. Sidecar checks alone do not
 * establish that no writer is active.
 */
#include <sqlite3.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <sys/stat.h>
#define stat _stat
#else
#include <sys/stat.h>
#endif

static int sidecar_state(const char *path, const char *suffix) {
    char *name;
    struct stat st;
    size_t n = strlen(path), s = strlen(suffix);
    name = (char *)malloc(n + s + 1);
    if (!name) return -1;
    memcpy(name, path, n);
    memcpy(name + n, suffix, s + 1);
    int found = stat(name, &st) == 0 ? 1 : (errno == ENOENT ? 0 : -1);
    free(name);
    return found;
}

static int reject_sidecars(const char *path) {
    int wal = sidecar_state(path, "-wal");
    int journal = sidecar_state(path, "-journal");
    int shm = sidecar_state(path, "-shm");
    if (wal < 0 || journal < 0 || shm < 0 || wal || journal || shm) {
        fprintf(stderr, "sidecar exists or cannot be checked: %s\n", path);
        return 1;
    }
    return 0;
}

static int scalar_int(sqlite3 *db, const char *sql, int *out) {
    sqlite3_stmt *st = NULL;
    int rc = sqlite3_prepare_v2(db, sql, -1, &st, NULL);
    if (rc == SQLITE_OK) rc = sqlite3_step(st);
    if (rc == SQLITE_ROW) {
        *out = sqlite3_column_int(st, 0);
        rc = SQLITE_OK;
    }
    sqlite3_finalize(st);
    return rc;
}

static int prefix_count(sqlite3 *db, const char *glob, int *out) {
    static const char sql[] =
        "SELECT count(*) FROM keyentry "
        "WHERE domain = 2 AND namespace = 103 "
        "AND CAST(alias AS TEXT) GLOB ?1";
    sqlite3_stmt *st = NULL;
    int rc = sqlite3_prepare_v2(db, sql, -1, &st, NULL);
    if (rc != SQLITE_OK) return rc;
    char pattern[64];
    int n = snprintf(pattern, sizeof(pattern), "%s", glob);
    if (n < 0 || (size_t)n >= sizeof(pattern)) {
        sqlite3_finalize(st);
        return SQLITE_TOOBIG;
    }
    rc = sqlite3_bind_text(st, 1, pattern, n, SQLITE_TRANSIENT);
    if (rc == SQLITE_OK) rc = sqlite3_step(st);
    if (rc == SQLITE_ROW) {
        *out = sqlite3_column_int(st, 0);
        rc = SQLITE_OK;
    }
    sqlite3_finalize(st);
    return rc;
}

static int inspect_db(const char *path, int index) {
    sqlite3 *db = NULL;
    char uri[4096];
    int version, synthetic_count, usrskey_count, rc;
    if (reject_sidecars(path)) return 2;
    if (snprintf(uri, sizeof(uri), "file:%s?mode=ro&immutable=1", path) >= (int)sizeof(uri)) {
        fprintf(stderr, "database path too long\n");
        return 2;
    }
    rc = sqlite3_open_v2(uri, &db, SQLITE_OPEN_READONLY | SQLITE_OPEN_URI, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "open failed for database %d\n", index);
        sqlite3_close(db);
        return 2;
    }
    /* journal_mode returns text; WAL is unsafe for an immutable snapshot. */
    {
        sqlite3_stmt *st = NULL;
        rc = sqlite3_prepare_v2(db, "PRAGMA journal_mode", -1, &st, NULL);
        if (rc == SQLITE_OK && sqlite3_step(st) == SQLITE_ROW) {
            const unsigned char *mode = sqlite3_column_text(st, 0);
            if (!mode) rc = SQLITE_ERROR;
            else if (sqlite3_stricmp((const char *)mode, "wal") == 0) rc = SQLITE_BUSY;
        }
        else if (rc == SQLITE_OK) rc = SQLITE_ERROR;
        sqlite3_finalize(st);
        if (rc != SQLITE_OK) {
            fprintf(stderr, "journal mode check failed or returned WAL for database %d\n", index);
            sqlite3_close(db);
            return 2;
        }
    }
    rc = scalar_int(db, "SELECT version FROM version WHERE id=0", &version);
    if (rc == SQLITE_OK) rc = prefix_count(db, "synthetic_password_*", &synthetic_count);
    if (rc == SQLITE_OK) rc = prefix_count(db, "USRSKEY_synthetic_password_*", &usrskey_count);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "schema query failed for database %d\n", index);
        sqlite3_close(db);
        return 2;
    }
    printf("db%d schema_version=%d synthetic_password_count=%d USRSKEY_synthetic_password_count=%d\n",
           index, version, synthetic_count, usrskey_count);
    sqlite3_close(db);
    return 0;
}

static int self_test(void) {
    sqlite3 *db = NULL;
    int rc = sqlite3_open(":memory:", &db);
    if (rc == SQLITE_OK) rc = sqlite3_exec(db,
        "CREATE TABLE version(id INTEGER PRIMARY KEY, version INTEGER);"
        "INSERT INTO version VALUES(0,7);"
        "CREATE TABLE keyentry(domain INTEGER, namespace INTEGER, alias TEXT);"
        "INSERT INTO keyentry VALUES(2,103,'synthetic_password_demo'),(2,103,'USRSKEY_synthetic_password_demo'),(1,103,'synthetic_password_other');",
        NULL, NULL, NULL);
    if (rc == SQLITE_OK) {
        int v, a, b;
        rc = scalar_int(db, "SELECT version FROM version WHERE id=0", &v);
        if (rc == SQLITE_OK) rc = prefix_count(db, "synthetic_password_*", &a);
        if (rc == SQLITE_OK) rc = prefix_count(db, "USRSKEY_synthetic_password_*", &b);
        if (rc == SQLITE_OK && (v != 7 || a != 1 || b != 1)) rc = SQLITE_ERROR;
        if (rc == SQLITE_OK) puts("self-test: ok");
    }
    sqlite3_close(db);
    return rc == SQLITE_OK ? 0 : 1;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc != 3) {
        fprintf(stderr, "usage: %s --self-test | %s DATABASE_A DATABASE_B\n", argv[0], argv[0]);
        return 64;
    }
    if (strcmp(argv[1], "/tmp/a25-keystore2-db/persistent.sqlite") != 0 ||
        strcmp(argv[2], "/data/misc/keystore/persistent.sqlite") != 0) {
        fprintf(stderr, "expected the two authorized A25 database paths\n");
        return 64;
    }
    int rc = inspect_db(argv[1], 1);
    if (rc == 0) rc = inspect_db(argv[2], 2);
    return rc;
}
