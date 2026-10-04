package net.gamecodex.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.res.AssetManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public class MainActivity extends Activity {
    private static final int PICK_PACK = 4105;
    private WebView webView;
    private File codexDir;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(7, 10, 16));
        getWindow().setNavigationBarColor(Color.rgb(7, 10, 16));

        codexDir = new File(getFilesDir(), "codex");
        try {
            ensureBundledCodex();
        } catch (IOException e) {
            Toast.makeText(this, "Failed to initialize Codex: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(7, 10, 16));
        webView.setOverScrollMode(WebView.OVER_SCROLL_NEVER);
        setContentView(webView);
        configureWebView();
        loadCodex();
    }

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(false);
        s.setTextZoom(100);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new CodexBridge(), "AndroidCodex");
    }

    private void loadCodex() {
        File index = new File(codexDir, "index.html");
        if (!index.isFile()) {
            Toast.makeText(this, "Codex pack has no index.html", Toast.LENGTH_LONG).show();
            return;
        }
        webView.loadUrl(Uri.fromFile(index).toString());
    }

    public final class CodexBridge {
        @JavascriptInterface
        public void choosePack() {
            runOnUiThread(() -> MainActivity.this.choosePack());
        }

        @JavascriptInterface
        public void restoreBundledPack() {
            runOnUiThread(() -> MainActivity.this.confirmRestore());
        }

        @JavascriptInterface
        public void reload() {
            runOnUiThread(() -> MainActivity.this.loadCodex());
        }

        @JavascriptInterface
        public void appInfo() {
            runOnUiThread(() -> {
                Intent i = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + getPackageName()));
                startActivity(i);
            });
        }
    }

    private void confirmRestore() {
        new AlertDialog.Builder(this)
                .setTitle("Restore bundled database?")
                .setMessage("This replaces the currently imported local Codex pack.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Restore", (d, w) -> {
                    try {
                        deleteTree(codexDir);
                        copyAssetTree("codex", codexDir);
                        prepareCatalogJs(codexDir);
                        loadCodex();
                    } catch (IOException e) {
                        Toast.makeText(this, "Restore failed: " + e.getMessage(), Toast.LENGTH_LONG).show();
                    }
                }).show();
    }

    private void choosePack() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType("application/zip");
        i.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/zip", "application/x-zip-compressed", "application/octet-stream"});
        startActivityForResult(i, PICK_PACK);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_PACK || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        File staging = new File(getCacheDir(), "codex-import-" + System.currentTimeMillis());
        try {
            unzipPack(uri, staging);
            File root = findPackRoot(staging);
            validatePack(root);
            prepareCatalogJs(root);
            File replacement = new File(getFilesDir(), "codex.new");
            deleteTree(replacement);
            copyTree(root, replacement);
            deleteTree(codexDir);
            if (!replacement.renameTo(codexDir)) {
                copyTree(replacement, codexDir);
                deleteTree(replacement);
            }
            Toast.makeText(this, "Codex database updated", Toast.LENGTH_SHORT).show();
            loadCodex();
        } catch (Exception e) {
            Toast.makeText(this, "Import failed: " + e.getMessage(), Toast.LENGTH_LONG).show();
        } finally {
            try { deleteTree(staging); } catch (Exception ignored) {}
        }
    }

    private void unzipPack(Uri uri, File dest) throws IOException {
        deleteTree(dest);
        if (!dest.mkdirs()) throw new IOException("Cannot create staging directory");
        try (InputStream raw = getContentResolver().openInputStream(uri);
             ZipInputStream zin = new ZipInputStream(new BufferedInputStream(raw))) {
            ZipEntry entry;
            byte[] buf = new byte[64 * 1024];
            String rootPath = dest.getCanonicalPath() + File.separator;
            while ((entry = zin.getNextEntry()) != null) {
                File out = new File(dest, entry.getName());
                String canonical = out.getCanonicalPath();
                if (!canonical.startsWith(rootPath)) throw new IOException("Unsafe ZIP entry");
                if (entry.isDirectory()) {
                    if (!out.exists() && !out.mkdirs()) throw new IOException("Cannot create " + entry.getName());
                } else {
                    File parent = out.getParentFile();
                    if (parent != null && !parent.exists() && !parent.mkdirs()) throw new IOException("Cannot create pack folder");
                    try (BufferedOutputStream bout = new BufferedOutputStream(new FileOutputStream(out))) {
                        int n;
                        while ((n = zin.read(buf)) > 0) bout.write(buf, 0, n);
                    }
                }
                zin.closeEntry();
            }
        }
    }

    private File findPackRoot(File staging) {
        if (new File(staging, "index.html").isFile()) return staging;
        File[] children = staging.listFiles(File::isDirectory);
        if (children != null && children.length == 1 && new File(children[0], "index.html").isFile()) return children[0];
        return staging;
    }

    private void validatePack(File root) throws IOException {
        if (!new File(root, "index.html").isFile()) throw new IOException("Not a Game Codex portable pack");
        if (!new File(root, "data/catalog.json").isFile() && !new File(root, "data/catalog.js").isFile())
            throw new IOException("Game Codex catalog missing");
    }

    private void ensureBundledCodex() throws IOException {
        File marker = new File(codexDir, ".bundled-v8");
        if (!new File(codexDir, "index.html").isFile() || !marker.exists()) {
            deleteTree(codexDir);
            copyAssetTree("codex", codexDir);
            prepareCatalogJs(codexDir);
            if (!marker.exists()) marker.createNewFile();
        }
    }

    private void copyAssetTree(String assetPath, File dest) throws IOException {
        AssetManager am = getAssets();
        String[] children = am.list(assetPath);
        if (children == null) return;
        if (children.length == 0) {
            File parent = dest.getParentFile();
            if (parent != null && !parent.exists()) parent.mkdirs();
            try (InputStream in = am.open(assetPath); FileOutputStream out = new FileOutputStream(dest)) {
                byte[] buf = new byte[32 * 1024];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            }
            return;
        }
        if (!dest.exists() && !dest.mkdirs()) throw new IOException("Cannot create " + dest);
        for (String child : children) copyAssetTree(assetPath + "/" + child, new File(dest, child));
    }

    private void prepareCatalogJs(File root) throws IOException {
        File json = new File(root, "data/catalog.json");
        File js = new File(root, "data/catalog.js");
        if (json.isFile() && !js.isFile()) {
            String body = new String(Files.readAllBytes(json.toPath()), StandardCharsets.UTF_8);
            Files.write(js.toPath(), ("window.CODEX_CATALOG=" + body + ";").getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void copyTree(File src, File dst) throws IOException {
        if (src.isDirectory()) {
            if (!dst.exists() && !dst.mkdirs()) throw new IOException("Cannot create " + dst);
            File[] files = src.listFiles();
            if (files != null) for (File f : files) copyTree(f, new File(dst, f.getName()));
        } else {
            File parent = dst.getParentFile();
            if (parent != null && !parent.exists()) parent.mkdirs();
            try (InputStream in = new FileInputStream(src); FileOutputStream out = new FileOutputStream(dst)) {
                byte[] buf = new byte[64 * 1024];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            }
        }
    }

    private static void deleteTree(File file) throws IOException {
        if (file == null || !file.exists()) return;
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) for (File c : children) deleteTree(c);
        }
        if (!file.delete()) throw new IOException("Cannot delete " + file);
    }

    @Override
    public void onBackPressed() {
        webView.evaluateJavascript("(window.codexBack&&window.codexBack())?'handled':'exit'", value -> {
            if (value == null || value.contains("exit")) MainActivity.super.onBackPressed();
        });
    }
}
