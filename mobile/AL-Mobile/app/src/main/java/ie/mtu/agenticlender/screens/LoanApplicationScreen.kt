package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.google.firebase.auth.FirebaseAuth
import ie.mtu.agenticlender.api.ApplicationRepository
import ie.mtu.agenticlender.api.ApplicationRequest
import ie.mtu.agenticlender.api.ApplicationSubmissionResult
import ie.mtu.agenticlender.api.Financials
import ie.mtu.agenticlender.api.ValuationDraft
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

@Composable
fun LoanApplicationScreen(valuationDraft: ValuationDraft?) {
    var buyerType by remember { mutableStateOf("") }
    var grossAnnualIncome by remember { mutableStateOf("") }
    var monthlyDebts by remember { mutableStateOf("") }
    var deposit by remember { mutableStateOf("") }
    var loanAmount by remember { mutableStateOf("") }
    var termYears by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf("") }
    var fieldErrors by remember { mutableStateOf(emptyMap<String, String>()) }
    var successMessage by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var applicationReference by remember { mutableStateOf("") }
    var applicationStatus by remember { mutableStateOf("") }
    var applicationStatusLabel by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text("Loan Application", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(16.dp))

        Text("Buyer Type", style = MaterialTheme.typography.titleMedium)
        Row {
            RadioButton(
                selected = buyerType == "first_time",
                onClick = { buyerType = "first_time" }
            )
            Text("First Time Buyer", modifier = Modifier.padding(top = 12.dp))
        }
        Row {
            RadioButton(
                selected = buyerType == "subsequent",
                onClick = { buyerType = "subsequent" }
            )
            Text("Subsequent Buyer", modifier = Modifier.padding(top = 12.dp))
        }

        Spacer(modifier = Modifier.height(12.dp))
        OutlinedTextField(
            value = grossAnnualIncome,
            onValueChange = { grossAnnualIncome = it },
            label = { Text("Gross Annual Income (€)") },
            isError = fieldErrors.containsKey("financials.grossAnnualIncome"),
            supportingText = {
                fieldErrors["financials.grossAnnualIncome"]?.let { Text(it) }
            },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = monthlyDebts,
            onValueChange = { monthlyDebts = it },
            label = { Text("Monthly Debts (€)") },
            isError = fieldErrors.containsKey("financials.monthlyDebts"),
            supportingText = {
                fieldErrors["financials.monthlyDebts"]?.let { Text(it) }
            },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = deposit,
            onValueChange = { deposit = it },
            label = { Text("Deposit (€)") },
            isError = fieldErrors.containsKey("financials.deposit"),
            supportingText = {
                fieldErrors["financials.deposit"]?.let { Text(it) }
            },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = loanAmount,
            onValueChange = { loanAmount = it },
            label = { Text("Loan Amount (€)") },
            isError = fieldErrors.containsKey("financials.loanAmount"),
            supportingText = {
                fieldErrors["financials.loanAmount"]?.let { Text(it) }
            },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedTextField(
            value = termYears,
            onValueChange = { termYears = it },
            label = { Text("Term Length (Years)") },
            isError = fieldErrors.containsKey("financials.termYears"),
            supportingText = {
                fieldErrors["financials.termYears"]?.let { Text(it) }
            },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(12.dp))
        valuationDraft?.let { draft ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Valuation: ${draft.valuation.valuationId}")
                    Text("Estimate: €${draft.valuation.estimate}")
                    Text("Range: €${draft.valuation.low} – €${draft.valuation.high}")
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))
        Button(
            enabled = !loading,
            onClick = {
                errorMessage = ""
                fieldErrors = emptyMap()
                successMessage = ""

                val income = grossAnnualIncome.toDoubleOrNull()
                val debts = monthlyDebts.toDoubleOrNull()
                val depositAmount = deposit.toDoubleOrNull()
                val requestedLoan = loanAmount.toDoubleOrNull()
                val term = termYears.toIntOrNull()

                when {
                    valuationDraft == null ->
                        errorMessage = "Complete a property valuation before applying."
                    buyerType.isBlank() ->
                        errorMessage = "Please select a buyer type."
                    income == null || !income.isFinite() || income <= 0.0 ->
                        errorMessage = "Gross annual income must be greater than 0."
                    debts == null || !debts.isFinite() || debts < 0.0 ->
                        errorMessage = "Monthly debts must be 0 or greater."
                    depositAmount == null || !depositAmount.isFinite() || depositAmount < 0.0 ->
                        errorMessage = "Deposit must be 0 or greater."
                    requestedLoan == null || !requestedLoan.isFinite() || requestedLoan <= 0.0 ->
                        errorMessage = "Loan amount must be greater than 0."
                    term == null || term !in 5..35 ->
                        errorMessage = "Loan term must be between 5 and 35 years."
                    else -> {
                        loading = true
                        scope.launch {
                            try {
                                val idToken = FirebaseAuth.getInstance().currentUser
                                    ?.getIdToken(false)
                                    ?.await()
                                    ?.token
                                    ?: throw IllegalStateException(
                                        "Sign in before submitting an application."
                                    )

                                val request = ApplicationRequest(
                                    buyerType = buyerType,
                                    financials = Financials(
                                        grossAnnualIncome = income,
                                        monthlyDebts = debts,
                                        deposit = depositAmount,
                                        loanAmount = requestedLoan,
                                        termYears = term
                                    ),
                                    property = valuationDraft.property,
                                    valuationId = valuationDraft.valuation.valuationId
                                )

                                when (
                                    val result = ApplicationRepository()
                                        .submitApplication(idToken, request)
                                ) {
                                    is ApplicationSubmissionResult.Success -> {
                                        val application = result.application
                                        applicationReference =
                                            application.reference ?: application.id
                                        applicationStatus = application.status
                                        applicationStatusLabel = application.statusLabel
                                        successMessage = "Application submitted successfully."
                                    }
                                    is ApplicationSubmissionResult.Failure -> {
                                        errorMessage = result.message
                                        fieldErrors = result.fieldErrors
                                    }
                                }
                            } catch (e: Exception) {
                                errorMessage =
                                    e.message ?: "Unable to submit the application."
                            } finally {
                                loading = false
                            }
                        }
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (loading) "Submitting…" else "Submit Application")
        }

        Spacer(modifier = Modifier.height(16.dp))
        if (loading) {
            CircularProgressIndicator()
            Spacer(modifier = Modifier.height(12.dp))
        }
        if (errorMessage.isNotEmpty()) {
            Text(text = errorMessage, color = MaterialTheme.colorScheme.error)
        }
        if (successMessage.isNotEmpty()) {
            Text(text = successMessage, color = MaterialTheme.colorScheme.primary)
        }
        if (applicationReference.isNotEmpty()) {
            Spacer(modifier = Modifier.height(12.dp))
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Application Reference: $applicationReference")
                    Text("Status: $applicationStatus")
                    Text("Status Label: $applicationStatusLabel")
                }
            }
        }
    }
}
