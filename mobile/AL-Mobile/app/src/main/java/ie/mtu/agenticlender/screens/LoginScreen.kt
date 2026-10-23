package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun LoginScreen() {

    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    var errorMessage by remember { mutableStateOf("") }
    var successMessage by remember { mutableStateOf("") }

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

                        /*
                         * TODO US-102
                         *
                         * Firebase Authentication
                         *
                         * signInWithEmailAndPassword(
                         *      email,
                         *      password
                         * )
                         *
                         * On success:
                         * - Navigate to PropertyCheckerScreen
                         * - Firebase session should persist
                         *
                         * On failure:
                         * - Show "Invalid email or password"
                         *
                         * Acceptance Criteria:
                         * ✅ Login
                         * ✅ Logout
                         * ✅ Wrong credentials handled
                         * ✅ Session persists after restart
                         */

                        successMessage =
                            "Validation successful. Ready for Firebase sign in."
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Sign In")
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedButton(
            onClick = {

                /*
                 * TODO
                 *
                 * Navigate to RegisterScreen()
                 *
                 * Requires Navigation setup.
                 */

                successMessage =
                    "Register navigation placeholder."
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

                successMessage =
                    "Logout placeholder."
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