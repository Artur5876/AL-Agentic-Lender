package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.google.firebase.auth.FirebaseAuth
import ie.mtu.agenticlender.api.AffordabilityRepository
import ie.mtu.agenticlender.api.AffordabilityRequest
import ie.mtu.agenticlender.api.AffordabilityResponse
import ie.mtu.agenticlender.api.AffordabilityResult
import ie.mtu.agenticlender.estimate.INDICATIVE_NOTE
import ie.mtu.agenticlender.estimate.formatEuro
import ie.mtu.agenticlender.estimate.formatEuroWithCents
import ie.mtu.agenticlender.estimate.formatFraction
import ie.mtu.agenticlender.estimate.formatLti
import ie.mtu.agenticlender.estimate.limitedByText
import ie.mtu.agenticlender.estimate.validateEstimateInputs
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

// AL-3 US-111 Enter income, debts, deposit and term for borrowing estimate.
// The borrower enters their details; the backend (POST /affordability) works out the
// indicative maximum loan, LTI and LTV, and this screen shows them.
@Composable
fun BorrowingEstimateScreen(
    // Goes back to the screen you came from. Empty by default so old calls still work.
    onBack: () -> Unit = {}
) {
    // What the borrower has typed (kept as text, turned into numbers when they press the button)
    var buyerType by remember { mutableStateOf("") }
    var income by remember { mutableStateOf("") }
    var monthlyDebts by remember { mutableStateOf("") }
    var deposit by remember { mutableStateOf("") }
    var termYears by remember { mutableStateOf("") }

    // What's shown after pressing the button
    var loading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf("") }
    var estimate by remember { mutableStateOf<AffordabilityResponse?>(null) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text("How much could I borrow?", style = MaterialTheme.typography.headlineMedium)
        TextButton(onClick = onBack) { Text("← Back") }
        Spacer(modifier = Modifier.height(8.dp))

        // Buyer type: first-time buyers can borrow a bigger multiple of income
        Text("Buyer type", style = MaterialTheme.typography.titleMedium)
        Row(verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = buyerType == "first_time", onClick = { buyerType = "first_time" })
            Text("First-time buyer")
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = buyerType == "subsequent", onClick = { buyerType = "subsequent" })
            Text("Subsequent buyer")
        }

        Spacer(modifier = Modifier.height(8.dp))
        NumberField("Gross annual household income (€)", income) { income = it }
        NumberField("Existing monthly debts (€)", monthlyDebts) { monthlyDebts = it }
        NumberField("Deposit (€)", deposit) { deposit = it }
        NumberField("Mortgage term (years, 5 to 35)", termYears, wholeNumber = true) { termYears = it }

        Spacer(modifier = Modifier.height(16.dp))
        Button(
            enabled = !loading,
            modifier = Modifier.fillMaxWidth(),
            onClick = {
                errorMessage = ""
                estimate = null

                // Turn the text into numbers. toDoubleOrNull() gives null if it isn't a number.
                val incomeValue = income.toDoubleOrNull()
                val debtsValue = monthlyDebts.toDoubleOrNull()
                val depositValue = deposit.toDoubleOrNull()
                val termValue = termYears.toIntOrNull()

                // Check the inputs first, so we don't send something the API will reject
                val problem = validateEstimateInputs(buyerType, incomeValue, debtsValue, depositValue, termValue)
                if (problem != null) {
                    errorMessage = problem
                } else {
                    loading = true
                    // Calling the API takes time, so it runs in the background (a coroutine)
                    scope.launch {
                        try {
                            // The API needs the signed-in user's Firebase token
                            val idToken = FirebaseAuth.getInstance().currentUser
                                ?.getIdToken(false)?.await()?.token
                                ?: throw IllegalStateException("Please log in again.")

                            // "!!" means "this can't be empty here": validateEstimateInputs already checked it
                            val request = AffordabilityRequest(
                                buyerType = buyerType,
                                grossAnnualIncome = incomeValue!!,
                                monthlyDebts = debtsValue!!,
                                deposit = depositValue!!,
                                termYears = termValue!!
                            )

                            when (val result = AffordabilityRepository().getEstimate(idToken, request)) {
                                is AffordabilityResult.Success -> estimate = result.estimate
                                is AffordabilityResult.Failure -> errorMessage = result.message
                            }
                        } catch (e: Exception) {
                            errorMessage = e.message ?: "Couldn't get an estimate. Please try again."
                        } finally {
                            loading = false
                        }
                    }
                }
            }
        ) {
            Text("Get my estimate")
        }

        Spacer(modifier = Modifier.height(12.dp))
        if (loading) CircularProgressIndicator()
        if (errorMessage.isNotEmpty()) Text(errorMessage, color = MaterialTheme.colorScheme.error)

        // A local copy, so Kotlin knows it can't change while we use it
        val current = estimate
        if (current != null) EstimateCard(current)
    }
}

// The result: maximum loan, why it's limited, LTI, LTV, repayment, and the "indicative only" note
@Composable
private fun EstimateCard(estimate: AffordabilityResponse) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("You may be able to borrow up to")
            Text(
                text = formatEuro(estimate.maxLoan),
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            Text(limitedByText(estimate.limitedBy), style = MaterialTheme.typography.bodySmall)

            Spacer(modifier = Modifier.height(12.dp))
            Text("Loan-to-income (LTI): ${formatLti(estimate.lti)}")
            Text("Loan-to-value (LTV): ${formatFraction(estimate.ltv)}")
            Text("Monthly repayment: ${formatEuroWithCents(estimate.monthlyRepayment)}")

            Spacer(modifier = Modifier.height(12.dp))
            // Acceptance criteria: the "indicative only" note is always shown with the estimate
            Text(
                INDICATIVE_NOTE,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

// A text box that brings up the number keyboard
@Composable
private fun NumberField(label: String, value: String, wholeNumber: Boolean = false, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(
            keyboardType = if (wholeNumber) KeyboardType.Number else KeyboardType.Decimal
        ),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
    )
}