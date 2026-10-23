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
fun RegisterScreen() {

    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }

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
            text = "Create Account",
            style = MaterialTheme.typography.headlineMedium
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

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedTextField(
            value = confirmPassword,
            onValueChange = {
                confirmPassword = it
            },
            label = { Text("Confirm Password") },
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

                    password.length < 8 ->
                        errorMessage = "Password must be at least 8 characters"

                    confirmPassword.isBlank() ->
                        errorMessage = "Please confirm your password"

                    password != confirmPassword ->
                        errorMessage = "Passwords do not match"

                    else -> {

                        /*
                         * TODO US-101
                         *
                         * Firebase Auth:
                         *
                         * createUserWithEmailAndPassword(
                         *      email,
                         *      password
                         * )
                         *
                         * Then create Firestore user profile:
                         *
                         * users/{uid}
                         *
                         * {
                         *   "uid": uid,
                         *   "email": email,
                         *   "role": "borrower"
                         * }
                         *
                         * Acceptance Criteria:
                         * ✅ Firebase Auth account created
                         * ✅ Firestore profile created
                         * ✅ role = borrower
                         */

                        successMessage =
                            "Validation successful. Ready for Firebase registration."
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {

            Text("Register")
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