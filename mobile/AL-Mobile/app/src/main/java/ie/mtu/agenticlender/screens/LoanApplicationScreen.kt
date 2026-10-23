package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun LoanApplicationScreen() {

    var buyerType by remember { mutableStateOf("") }

    var grossAnnualIncome by remember { mutableStateOf("") }
    var monthlyDebts by remember { mutableStateOf("") }
    var deposit by remember { mutableStateOf("") }
    var loanAmount by remember { mutableStateOf("") }
    var termYears by remember { mutableStateOf("") }

    var errorMessage by remember { mutableStateOf("") }
    var successMessage by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {

        Text(
            text = "Loan Application",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Buyer Type",
            style = MaterialTheme.typography.titleMedium
        )

        Row {
            RadioButton(
                selected = buyerType == "first_time",
                onClick = {
                    buyerType = "first_time"
                }
            )

            Text(
                text = "First Time Buyer",
                modifier = Modifier.padding(top = 12.dp)
            )
        }

        Row {
            RadioButton(
                selected = buyerType == "subsequent",
                onClick = {
                    buyerType = "subsequent"
                }
            )

            Text(
                text = "Subsequent Buyer",
                modifier = Modifier.padding(top = 12.dp)
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedTextField(
            value = grossAnnualIncome,
            onValueChange = { grossAnnualIncome = it },
            label = { Text("Gross Annual Income (€)") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = monthlyDebts,
            onValueChange = { monthlyDebts = it },
            label = { Text("Monthly Debts (€)") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = deposit,
            onValueChange = { deposit = it },
            label = { Text("Deposit (€)") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = loanAmount,
            onValueChange = { loanAmount = it },
            label = { Text("Loan Amount (€)") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = termYears,
            onValueChange = { termYears = it },
            label = { Text("Term Length (Years)") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = {

                errorMessage = ""
                successMessage = ""

                when {

                    buyerType.isBlank() ->
                        errorMessage = "Please select a buyer type"

                    grossAnnualIncome.isBlank() ->
                        errorMessage = "Gross annual income is required"

                    monthlyDebts.isBlank() ->
                        errorMessage = "Monthly debts are required"

                    deposit.isBlank() ->
                        errorMessage = "Deposit amount is required"

                    loanAmount.isBlank() ->
                        errorMessage = "Loan amount is required"

                    termYears.isBlank() ->
                        errorMessage = "Loan term is required"

                    termYears.toIntOrNull() == null ->
                        errorMessage = "Loan term must be a number"

                    termYears.toInt() !in 5..35 ->
                        errorMessage = "Loan term must be between 5 and 35 years"

                    else -> {

                        /*
                         * TODO US-112
                         *
                         * POST /applications
                         *
                         * Send:
                         * buyerType
                         * grossAnnualIncome
                         * monthlyDebts
                         * deposit
                         * loanAmount
                         * termYears
                         *
                         * Property details and valuationId
                         * should come from PropertyCheckerScreen.
                         *
                         * Backend requires:
                         * Authorization: Bearer <Firebase ID Token>
                         *
                         * Once Firebase auth is configured:
                         *
                         * Firebase.auth.currentUser
                         *      ?.getIdToken(false)
                         *
                         * Attach token to request header.
                         */

                        successMessage =
                            "Application validated successfully and is ready for API submission."
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Submit Application")
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