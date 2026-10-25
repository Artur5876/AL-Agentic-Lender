package ie.mtu.agenticlender.screens

import android.content.Context
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import android.util.Log
import com.google.firebase.FirebaseNetworkException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.FirebaseAuthInvalidUserException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.Proxy
import java.net.ProxySelector
import java.net.URI
import java.util.concurrent.TimeUnit

private object AuthEmulatorConnectivityTest {
    private const val TAG = "AuthEmulatorProbe"

    private val client = OkHttpClient.Builder()
        .callTimeout(10, TimeUnit.SECONDS)
        .build()

    private val endpoints = listOf(
        "http://192.168.0.50:8000/health",
        "http://192.168.0.50:8080",
        "http://192.168.0.50:9099"
    )

    // Reports Android/OkHttp proxy selection, then tests each local service with this same client.
    suspend fun run(context: Context): String = withContext(Dispatchers.IO) {
        buildString {
            appendLine("OkHttp client proxy: ${client.proxy ?: "<default selector>"}")
            appendLine("OkHttp proxy selector: ${client.proxySelector}")
            appendLine("Default proxy selector: ${ProxySelector.getDefault()}")
            appendLine("Android global http_proxy: ${setting(context, Settings.Global.HTTP_PROXY)}")
            appendLine("Android global proxy host: ${setting(context, "global_http_proxy_host")}")
            appendLine("Android global proxy port: ${setting(context, "global_http_proxy_port")}")
            appendLine("Android global PAC URL: ${setting(context, "global_proxy_pac_url")}")
            appendLine("Process proxy environment:")
            listOf("http_proxy", "https_proxy", "all_proxy", "no_proxy").forEach { key ->
                appendLine("  $key=${System.getenv(key) ?: "<unset>"}")
            }
            appendLine("JVM proxy properties:")
            listOf(
                "http.proxyHost", "http.proxyPort", "http.nonProxyHosts",
                "https.proxyHost", "https.proxyPort", "https.nonProxyHosts",
                "socksProxyHost", "socksProxyPort", "java.net.useSystemProxies"
            ).forEach { key ->
                appendLine("  $key=${System.getProperty(key) ?: "<unset>"}")
            }

            endpoints.forEach { url ->
                val uri = URI(url)
                appendLine("\n=== $url ===")
                try {
                    val selector = client.proxySelector ?: ProxySelector.getDefault()
                    val proxies = selector?.select(uri).orEmpty()
                    appendLine("Selected proxies: ${proxies.joinToString { proxy ->
                        val address = when (val socketAddress = proxy.address()) {
                            is java.net.InetSocketAddress ->
                                "${socketAddress.hostString}:${socketAddress.port}"
                            else -> socketAddress?.toString() ?: "<no address>"
                        }
                        "${proxy.type()} $address"
                    }.ifEmpty { "<none>" }}")

                    val request = Request.Builder().url(url).get().build()
                    client.newCall(request).execute().use { response ->
                        appendLine("HTTP ${response.code} ${response.message}")
                        appendLine("Protocol: ${response.protocol}")
                        appendLine("Headers:\n${response.headers}")
                        appendLine("Body:\n${response.body?.string() ?: "<empty>"}")
                    }
                } catch (exception: Exception) {
                    Log.e(TAG, "Request to $url failed", exception)
                    appendLine("REQUEST FAILED: ${exception.javaClass.name}: ${exception.message}")
                }
            }
        }
    }

    private fun setting(context: Context, name: String): String =
        try {
            Settings.Global.getString(context.contentResolver, name) ?: "<unset>"
        } catch (exception: SecurityException) {
            Log.w(TAG, "Cannot read Android proxy setting $name", exception)
            "<unavailable: ${exception.message}>"
        }
}

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    onRegisterClick: () -> Unit
) {

    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    var errorMessage by remember { mutableStateOf("") }
    var successMessage by remember { mutableStateOf("") }
    var probeResult by remember { mutableStateOf("") }
    var probeRunning by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {

        Spacer(modifier = Modifier.height(60.dp))

        Text(
            text = "AL Agentic Lender",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Sign in to continue"
        )

        Spacer(modifier = Modifier.height(30.dp))

        OutlinedTextField(
            value = email,
            onValueChange = {
                email = it
            },
            label = { Text("Email") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedTextField(
            value = password,
            onValueChange = {
                password = it
            },
            label = { Text("Password") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = {

                errorMessage = ""
                successMessage = ""

                when {

                    email.isBlank() ->
                        errorMessage = "Email is required"

                    !android.util.Patterns.EMAIL_ADDRESS
                        .matcher(email)
                        .matches() ->
                        errorMessage = "Enter a valid email address"

                    password.isBlank() ->
                        errorMessage = "Password is required"

                    else -> {

                        FirebaseAuth.getInstance()
                            .signInWithEmailAndPassword(email, password)
                            .addOnSuccessListener {

                                successMessage = "Login successful"
                                onLoginSuccess()

                            }
                            .addOnFailureListener { exception ->
                                Log.e("LoginScreen", "Firebase sign-in failed", exception)
                                errorMessage = when (exception) {
                                    is FirebaseNetworkException ->
                                        "Cannot reach Firebase Auth emulator at 192.168.0.50:9099. Check that it is running."
                                    is FirebaseAuthInvalidCredentialsException,
                                    is FirebaseAuthInvalidUserException ->
                                        "Invalid email or password"
                                    else ->
                                        exception.localizedMessage ?: "Sign-in failed"
                                }

                            }
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Sign In")
        }

        Spacer(modifier = Modifier.height(8.dp))

        // This raw OkHttp request tests emulator connectivity without using FirebaseAuth.
        OutlinedButton(
            onClick = {
                probeRunning = true
                probeResult = "Testing API, Firestore, and Auth at 192.168.0.50..."
                scope.launch {
                    probeResult = AuthEmulatorConnectivityTest.run(context)
                    probeRunning = false
                    Log.i("AuthEmulatorProbe", probeResult)
                }
            },
            enabled = !probeRunning,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (probeRunning) "Testing Endpoints..." else "Test Emulator/API Connectivity")
        }

        if (probeResult.isNotEmpty()) {
            Text(
                text = probeResult,
                style = MaterialTheme.typography.bodySmall
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedButton(
            onClick = {
                onRegisterClick()
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Create Account")
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedButton(
            onClick = {

                /*
                 * TODO US-102
                 *
                 * Firebase.auth.signOut()
                 *
                 * Clear session
                 * Return to LoginScreen
                 */

                FirebaseAuth.getInstance().signOut()

                successMessage = "Logged out successfully"
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Logout")
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (errorMessage.isNotEmpty()) {

            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.error
            )
        }

        if (successMessage.isNotEmpty()) {

            Text(
                text = successMessage,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}