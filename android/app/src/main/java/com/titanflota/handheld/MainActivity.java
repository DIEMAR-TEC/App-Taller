package com.titanflota.handheld;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.KeyEvent;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;

import org.json.JSONObject;

/**
 * La app de la terminal con lector: una ventana web que abre /handheld del
 * servidor de Titán Flota.
 *
 * La lógica vive en el servidor (handheld.html), así un cambio en la
 * pantalla llega a todas las terminales sin reinstalar. Lo que agrega la
 * app es lo que una página no puede hacer sola:
 *   - recibir el código del lector cuando la terminal lo manda por aviso
 *     del sistema (broadcast) en lugar de escribirlo como teclado;
 *   - dar permiso de cámara a la página;
 *   - recordar la dirección del servidor.
 */
public class MainActivity extends Activity {

    static final String SERVIDOR_PREDETERMINADO = "https://app-taller-cu5d.onrender.com";
    static final String PANTALLA = "/handheld";
    static final int PEDIDO_CAMARA = 1;

    /*
     * Los avisos que mandan los lectores de las marcas más comunes. Cada
     * fabricante usa su nombre; en las terminales que se configuran (Zebra
     * DataWedge, Honeywell) se elige uno de estos o se deja el modo teclado,
     * que no necesita nada de esto.
     */
    static final String[] ACCIONES = {
        "com.titanflota.handheld.SCAN",            // Zebra DataWedge / configurable
        "com.symbol.datawedge.api.RESULT_ACTION",
        "com.honeywell.decode.intent.action.EDIT_DATA",
        "com.honeywell.scan.broadcast",
        "android.intent.ACTION_DECODE_DATA",       // Urovo, iData
        "android.intent.action.SCANRESULT",        // iData
        "com.sunmi.scanner.ACTION_DATA_CODE_RECEIVED",
        "com.scanner.broadcast",                   // Chainway
        "nlscan.action.SCANNER_RESULT",            // Newland
        "com.android.server.scannerservice.broadcast",
        "scan.rcv.message",
        "com.barcode.sendBroadcast",
        "com.android.scanner.broadcast",
        "com.xcheng.scanner.action.BARCODE_DECODING_BROADCAST",
    };
    static final String[] CLAVES = {
        "com.symbol.datawedge.data_string", "data", "barcode_string", "barcodeData",
        "value", "scannerdata", "SCAN_BARCODE1", "barcode", "decode_rslt",
        "EXTRA_BARCODE_DECODING_DATA", "code", "result",
    };

    WebView web;
    PermissionRequest camaraPendiente;

    final BroadcastReceiver lector = new BroadcastReceiver() {
        @Override
        public void onReceive(Context contexto, Intent intent) {
            String codigo = leerCodigo(intent);
            if (codigo == null || codigo.trim().isEmpty() || web == null) return;
            String js = "window.alEscanear && window.alEscanear("
                    + JSONObject.quote(codigo.trim()) + ")";
            web.evaluateJavascript(js, null);
        }
    };

    static String leerCodigo(Intent intent) {
        Bundle extras = intent.getExtras();
        if (extras == null) return null;
        for (String clave : CLAVES) {
            Object valor = extras.get(clave);
            if (valor instanceof String) return (String) valor;
            if (valor instanceof byte[]) return new String((byte[]) valor);
        }
        return null;
    }

    SharedPreferences prefs() {
        return getSharedPreferences("titan", MODE_PRIVATE);
    }

    String servidor() {
        return prefs().getString("servidor", SERVIDOR_PREDETERMINADO);
    }

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        web = new WebView(this);
        setContentView(web);

        WebSettings ajustes = web.getSettings();
        ajustes.setJavaScriptEnabled(true);
        ajustes.setDomStorageEnabled(true);
        ajustes.setMediaPlaybackRequiresUserGesture(false);
        ajustes.setUserAgentString(ajustes.getUserAgentString() + " TitanHandheld/1.0");

        CookieManager galletas = CookieManager.getInstance();
        galletas.setAcceptCookie(true);
        galletas.setAcceptThirdPartyCookies(web, true);

        web.addJavascriptInterface(new Puente(), "TitanApp");
        web.setWebViewClient(new Cliente());
        web.setWebChromeClient(new Cromo());

        if (guardado != null) web.restoreState(guardado);
        else web.loadUrl(servidor() + PANTALLA);
    }

    @Override
    protected void onSaveInstanceState(Bundle estado) {
        super.onSaveInstanceState(estado);
        web.saveState(estado);
    }

    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filtro = new IntentFilter();
        for (String accion : ACCIONES) filtro.addAction(accion);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(lector, filtro, Context.RECEIVER_EXPORTED);
        } else {
            registerReceiver(lector, filtro);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        try { unregisterReceiver(lector); } catch (IllegalArgumentException ignorado) { }
        CookieManager.getInstance().flush();
    }

    @Override
    public boolean onKeyDown(int tecla, KeyEvent evento) {
        if (tecla == KeyEvent.KEYCODE_BACK && web.canGoBack()) {
            web.goBack();
            return true;
        }
        return super.onKeyDown(tecla, evento);
    }

    /** Pedir la dirección del servidor y guardarla. */
    void cambiarServidor() {
        final EditText campo = new EditText(this);
        campo.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        campo.setText(servidor());
        new AlertDialog.Builder(this)
            .setTitle("Dirección del servidor")
            .setView(campo)
            .setPositiveButton("Guardar", (d, w) -> {
                String valor = campo.getText().toString().trim();
                while (valor.endsWith("/")) valor = valor.substring(0, valor.length() - 1);
                if (!valor.startsWith("http")) valor = "https://" + valor;
                prefs().edit().putString("servidor", valor).apply();
                web.loadUrl(valor + PANTALLA);
            })
            .setNeutralButton("Predeterminado", (d, w) -> {
                prefs().edit().remove("servidor").apply();
                web.loadUrl(SERVIDOR_PREDETERMINADO + PANTALLA);
            })
            .setNegativeButton("Cancelar", null)
            .show();
    }

    /** Lo que la página puede pedirle a la app. */
    class Puente {
        @JavascriptInterface
        public void cambiarServidor() {
            runOnUiThread(MainActivity.this::cambiarServidor);
        }

        @JavascriptInterface
        public String version() {
            return "1.0";
        }
    }

    class Cliente extends WebViewClient {
        /* Lo que es del servidor se abre acá; cualquier otro enlace, afuera. */
        @Override
        public boolean shouldOverrideUrlLoading(WebView vista, WebResourceRequest pedido) {
            Uri destino = pedido.getUrl();
            Uri propio = Uri.parse(servidor());
            if (destino.getHost() != null && destino.getHost().equals(propio.getHost())) return false;
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, destino));
            } catch (Exception ignorado) { }
            return true;
        }

        @Override
        public void onReceivedError(WebView vista, WebResourceRequest pedido, WebResourceError error) {
            if (!pedido.isForMainFrame()) return;
            String html = "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
                + "<style>body{font-family:sans-serif;padding:24px;color:#14243a}"
                + "button{display:block;width:100%;margin-top:14px;padding:16px;font-size:17px;"
                + "font-weight:bold;border:0;border-radius:10px;background:#2563eb;color:#fff}"
                + "button.alt{background:#e9eef4;color:#14243a}</style></head><body>"
                + "<h2>Sin conexión con el servidor</h2><p>" + servidor() + "</p>"
                + "<button onclick=\"location.href='" + servidor() + PANTALLA + "'\">Reintentar</button>"
                + "<button class='alt' onclick='TitanApp.cambiarServidor()'>Cambiar servidor</button>"
                + "</body></html>";
            vista.loadDataWithBaseURL(null, html, "text/html", "utf-8", null);
        }
    }

    class Cromo extends WebChromeClient {
        /* La página pide la cámara para leer QR: se le da si el sistema
           ya dio el permiso; si no, se pide y se responde después. */
        @Override
        public void onPermissionRequest(final PermissionRequest pedido) {
            runOnUiThread(() -> {
                if (Build.VERSION.SDK_INT < 23
                        || checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                    pedido.grant(pedido.getResources());
                } else {
                    camaraPendiente = pedido;
                    requestPermissions(new String[]{Manifest.permission.CAMERA}, PEDIDO_CAMARA);
                }
            });
        }
    }

    @Override
    public void onRequestPermissionsResult(int codigo, String[] permisos, int[] resultados) {
        if (codigo != PEDIDO_CAMARA || camaraPendiente == null) return;
        if (resultados.length > 0 && resultados[0] == PackageManager.PERMISSION_GRANTED) {
            camaraPendiente.grant(camaraPendiente.getResources());
        } else {
            camaraPendiente.deny();
        }
        camaraPendiente = null;
    }
}
