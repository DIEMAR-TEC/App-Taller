package com.titanflota.handheld;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
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

import org.json.JSONObject;

import java.util.ArrayList;

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
 *
 * La dirección del servidor es fija: la terminal la usan los empleados y
 * no tienen que poder cambiarla.
 */
public class MainActivity extends Activity {

    static final String SERVIDOR = "https://app.titanfleetmanagement.com";
    static final String PANTALLA = "/handheld";
    static final int PEDIDO_CAMARA = 1;
    static final int PEDIDO_MICROFONO = 2;
    static final int DICTADO_SISTEMA = 3;
    static final String ACCION_LECTOR = "com.titanflota.handheld.SCAN";

    /*
     * Los avisos que mandan los lectores de las marcas más comunes. Cada
     * fabricante usa su nombre; en las terminales que se configuran (Zebra
     * DataWedge, Honeywell) se elige uno de estos o se deja el modo teclado,
     * que no necesita nada de esto.
     */
    static final String[] ACCIONES = {
        ACCION_LECTOR,                             // Zebra: perfil que crea configurarDataWedge
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
    SpeechRecognizer reconocedor;

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

    String servidor() {
        return SERVIDOR;
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

        configurarDataWedge();

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

    /**
     * En las Zebra, un perfil de DataWedge para esta app: el lector manda el
     * código por broadcast a ACCION_LECTOR y no como teclado. Así no depende
     * de que el perfil general tenga el Enter activado. En equipos sin
     * DataWedge el aviso no lo recibe nadie y no pasa nada.
     */
    void configurarDataWedge() {
        Bundle perfil = new Bundle();
        perfil.putString("PROFILE_NAME", "TitanHandheld");
        perfil.putString("PROFILE_ENABLED", "true");
        perfil.putString("CONFIG_MODE", "CREATE_IF_NOT_EXIST");

        Bundle app = new Bundle();
        app.putString("PACKAGE_NAME", getPackageName());
        app.putStringArray("ACTIVITY_LIST", new String[]{"*"});
        perfil.putParcelableArray("APP_LIST", new Bundle[]{app});

        Bundle lectorParams = new Bundle();
        lectorParams.putString("scanner_selection", "auto");
        lectorParams.putString("scanner_input_enabled", "true");
        Bundle lector = new Bundle();
        lector.putString("PLUGIN_NAME", "BARCODE");
        lector.putString("RESET_CONFIG", "true");
        lector.putBundle("PARAM_LIST", lectorParams);

        Bundle intentParams = new Bundle();
        intentParams.putString("intent_output_enabled", "true");
        intentParams.putString("intent_action", ACCION_LECTOR);
        intentParams.putString("intent_delivery", "2");
        Bundle salida = new Bundle();
        salida.putString("PLUGIN_NAME", "INTENT");
        salida.putString("RESET_CONFIG", "true");
        salida.putBundle("PARAM_LIST", intentParams);

        Bundle tecladoParams = new Bundle();
        tecladoParams.putString("keystroke_output_enabled", "false");
        Bundle teclado = new Bundle();
        teclado.putString("PLUGIN_NAME", "KEYSTROKE");
        teclado.putString("RESET_CONFIG", "true");
        teclado.putBundle("PARAM_LIST", tecladoParams);

        perfil.putParcelableArrayList("PLUGIN_CONFIG",
                new ArrayList<>(java.util.Arrays.asList(lector, salida, teclado)));

        Intent pedido = new Intent("com.symbol.datawedge.api.ACTION");
        pedido.putExtra("com.symbol.datawedge.api.SET_CONFIG", perfil);
        sendBroadcast(pedido);
    }

    void js(String codigo) {
        runOnUiThread(() -> web.evaluateJavascript(codigo, null));
    }

    void dictadoError(String mensaje) {
        js("window.alDictarError && window.alDictarError(" + JSONObject.quote(mensaje) + ")");
    }

    void dictadoListo(String texto) {
        js("window.alDictar && window.alDictar(" + JSONObject.quote(texto) + ")");
    }

    /** Escuchar y devolver el texto a la página. */
    void dictar() {
        if (Build.VERSION.SDK_INT >= 23
                && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, PEDIDO_MICROFONO);
            return;
        }
        Intent pedido = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        pedido.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        pedido.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-AR");
        pedido.putExtra(RecognizerIntent.EXTRA_PROMPT, "Trabajo realizado");
        // Que no corte en la primera pausa: el gomero piensa entre una
        // cubierta y la otra.
        pedido.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 4000);
        pedido.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 4000);
        pedido.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 10000);

        if (SpeechRecognizer.isRecognitionAvailable(this)) {
            if (reconocedor == null) reconocedor = SpeechRecognizer.createSpeechRecognizer(this);
            reconocedor.setRecognitionListener(new Oyente());
            reconocedor.startListening(pedido);
            return;
        }
        try {
            startActivityForResult(pedido, DICTADO_SISTEMA);
        } catch (Exception e) {
            dictadoError("el equipo no tiene reconocimiento de voz instalado");
        }
    }

    @Override
    protected void onActivityResult(int codigo, int resultado, Intent datos) {
        super.onActivityResult(codigo, resultado, datos);
        if (codigo != DICTADO_SISTEMA) return;
        ArrayList<String> textos = datos == null ? null
                : datos.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
        if (resultado == RESULT_OK && textos != null && !textos.isEmpty()) dictadoListo(textos.get(0));
        else dictadoError("sin texto reconocido");
    }

    class Oyente implements RecognitionListener {
        @Override public void onResults(Bundle resultados) {
            ArrayList<String> textos = resultados.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (textos != null && !textos.isEmpty()) dictadoListo(textos.get(0));
            else dictadoError("sin texto reconocido");
        }
        @Override public void onError(int error) {
            String que;
            switch (error) {
                case SpeechRecognizer.ERROR_NO_MATCH:
                case SpeechRecognizer.ERROR_SPEECH_TIMEOUT: que = "no se entendió el audio"; break;
                case SpeechRecognizer.ERROR_NETWORK:
                case SpeechRecognizer.ERROR_NETWORK_TIMEOUT: que = "sin conexión para reconocer la voz"; break;
                case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS: que = "sin permiso de micrófono"; break;
                default: que = "error " + error + " del reconocedor de voz";
            }
            dictadoError(que);
        }
        @Override public void onReadyForSpeech(Bundle p) { }
        @Override public void onBeginningOfSpeech() { }
        @Override public void onRmsChanged(float r) { }
        @Override public void onBufferReceived(byte[] b) { }
        @Override public void onEndOfSpeech() { }
        @Override public void onPartialResults(Bundle p) { }
        @Override public void onEvent(int t, Bundle p) { }
    }

    /** Lo que la página puede pedirle a la app. */
    class Puente {
        @JavascriptInterface
        public void dictar() {
            runOnUiThread(MainActivity.this::dictar);
        }

        @JavascriptInterface
        public String version() {
            return "1.3";
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
                + "<h2>Sin conexión con el servidor</h2><p>Revisar el wifi o los datos.</p>"
                + "<button onclick=\"location.href='" + servidor() + PANTALLA + "'\">Reintentar</button>"
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
        if (codigo == PEDIDO_MICROFONO) {
            if (resultados.length > 0 && resultados[0] == PackageManager.PERMISSION_GRANTED) dictar();
            else dictadoError("sin permiso de micrófono");
            return;
        }
        if (codigo != PEDIDO_CAMARA || camaraPendiente == null) return;
        if (resultados.length > 0 && resultados[0] == PackageManager.PERMISSION_GRANTED) {
            camaraPendiente.grant(camaraPendiente.getResources());
        } else {
            camaraPendiente.deny();
        }
        camaraPendiente = null;
    }
}
