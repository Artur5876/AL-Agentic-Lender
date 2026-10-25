package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

import com.google.firebase.firestore.FieldValue
import android.util.Patterns


@Composable
fun RegisterScreen(
    onRegisterSuccess: () -> Unit,
    onBackToLogin: () -> Unit
) {

    var email by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }
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
            value = displayName,
            onValueChange = {
                displayName = it
            },
            label = { Text("Display Name") },
            modifier = Modifier.fillMaxWidth()
        )

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

                    displayName.isBlank() ->
                        errorMessage = "Display name is required"

                    email.isBlank() ->
                        errorMessage = "Email is required"

                    !Regex("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")
                        .matches(email) ->
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

                        val auth = FirebaseAuth.getInstance()

                        println("Register screen auth instance: ${auth.hashCode()}")

                        auth.createUserWithEmailAndPassword(
                            email,
                            password
                        )
                            .addOnSuccessListener { authResult ->

                                val uid = authResult.user?.uid ?: ""

                                FirebaseFirestore.getInstance()
                                    .collection("users")
                                    .document(uid)
                                    .set(
                                        mapOf(
                                            "uid" to uid,
                                            "email" to email,
                                            "displayName" to displayName,
                                            "role" to "borrower",
                                            "createdAt" to FieldValue.serverTimestamp()
                                        )
                                    )
                                    .addOnSuccessListener {

                                        successMessage =
                                            "Account created successfully."
                                        onRegisterSuccess()

                                    }
                                    .addOnFailureListener { e ->

                                        e.printStackTrace()

                                        errorMessage =
                                            "Firestore error: ${e.javaClass.simpleName} - ${e.message}"
                                    }
                            }
                            .addOnFailureListener { e ->

                                e.printStackTrace()

                                errorMessage =
                                    "Registration failed: ${e.javaClass.simpleName} - ${e.message}"
                            }
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {

            Text("Register")
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedButton(
            onClick = {
                onBackToLogin()
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Back to Login")
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