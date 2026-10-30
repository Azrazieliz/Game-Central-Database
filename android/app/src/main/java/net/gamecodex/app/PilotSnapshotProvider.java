package net.gamecodex.app;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.UriMatcher;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Binder;
import android.content.pm.PackageManager;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/**
 * Read-only Android IPC interface for the separate Asterion Pilot application.
 * No write operations or source data mutation are exposed.
 * The caller's installed UID must own com.gamepilot, not just use the authority URL.
 */
public final class PilotSnapshotProvider extends ContentProvider {
    public static final String AUTHORITY = "net.gamecodex.app.pilot";
    private static final String[] COLUMNS = {"schema_version", "payload_json", "snapshot_time"};
    private static final UriMatcher ROUTES = new UriMatcher(UriMatcher.NO_MATCH);
    static {
        ROUTES.addURI(AUTHORITY, "snapshot/global", 1);
        ROUTES.addURI(AUTHORITY, "snapshot/jp", 2);
        ROUTES.addURI(AUTHORITY, "snapshot/unassigned", 3);
    }

    @Override public boolean onCreate() { return true; }
    private void requirePilotCaller() {
        int uid = Binder.getCallingUid();
        String[] packages = getContext().getPackageManager().getPackagesForUid(uid);
        boolean allowed = false;
        if (packages != null) {
            for (String p : packages) {
                if (p.equals("com.gamepilot") || p.equals(getContext().getPackageName()))
                    allowed = true;
            }
        }
        if (!allowed) throw new SecurityException("Asterion Pilot integration caller required");
    }
    @Override public Cursor query(Uri uri, String[] projection, String selection,
                                   String[] selectionArgs, String sortOrder) {
        requirePilotCaller();
        int route = ROUTES.match(uri);
        if (route == UriMatcher.NO_MATCH) throw new IllegalArgumentException("Unsupported path");
        String account = route == 1 ? "global" : route == 2 ? "jp" : "unassigned";
        MatrixCursor rows = new MatrixCursor(COLUMNS);
        try {
            File file = new File(getContext().getFilesDir(), "pilot-snapshot-" + account + ".json");
            if (!file.isFile() || file.length() > 524288L) return rows;
            String value = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
            rows.addRow(new Object[]{1, value, file.lastModified()});
        } catch (Exception ignored) {
            // Empty cursor signals that no usable Codex snapshot is currently available.
        }
        return rows;
    }
    @Override public String getType(Uri uri) {
        requirePilotCaller();
        if (ROUTES.match(uri) == UriMatcher.NO_MATCH)
            throw new IllegalArgumentException("Unsupported path");
        return "vnd.android.cursor.item/vnd.asterion.codex.snapshot";
    }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new SecurityException("Read only"); }
    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { throw new SecurityException("Read only"); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) { throw new SecurityException("Read only"); }
}
