package ie.mtu.agenticlender.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ie.mtu.agenticlender.application.DTI_EXPLANATION
import ie.mtu.agenticlender.application.LTV_EXPLANATION
import ie.mtu.agenticlender.application.BorrowerApplication
import ie.mtu.agenticlender.application.PENDING_TEXT
import ie.mtu.agenticlender.application.checkText
import ie.mtu.agenticlender.application.formatPercent
import ie.mtu.agenticlender.application.formatTime
import ie.mtu.agenticlender.application.isPending
import ie.mtu.agenticlender.application.listenToLatestApplication
import ie.mtu.agenticlender.application.nextStepText
import ie.mtu.agenticlender.application.statusLabel
import ie.mtu.agenticlender.application.upcomingStatuses

// "My application" screen:
// - AL-8 US-132: the application's lifecycle state, with a timeline and timestamps, updating live
// - AL-7 US-131: LTV and DTI with a one-line explanation each, "Pending" until the AI committee is done
@Composable
fun MyApplicationScreen(
    // Goes back to the screen you came from. Empty by default so old calls still work.
    onBack: () -> Unit = {}
) {
    var application by remember { mutableStateOf<BorrowerApplication?>(null) }
    var loading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf("") }

    // Start the live Firestore listener when the screen opens, and stop it when the screen closes
    DisposableEffect(Unit) {
        val registration = listenToLatestApplication(
            onChange = { latest ->
                application = latest
                loading = false
                errorMessage = ""
            },
            onError = { message ->
                errorMessage = message
                loading = false
            }
        )
        onDispose { registration?.remove() }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text("My Application", style = MaterialTheme.typography.headlineMedium)

        // Back to the Property Checker or Loan Application, whichever you came from
        TextButton(onClick = onBack) {
            Text("← Back")
        }
        Spacer(modifier = Modifier.height(8.dp))

        // A local copy, so Kotlin knows it can't change while we use it
        val current = application

        when {
            loading -> CircularProgressIndicator()
            errorMessage.isNotEmpty() -> Text(errorMessage, color = MaterialTheme.colorScheme.error)
            current == null -> Text("You haven't submitted an application yet.")
            else -> ApplicationDetails(current)
        }
    }
}

// Everything shown once the application has loaded
@Composable
private fun ApplicationDetails(application: BorrowerApplication) {
    // Current status and what happens next
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Reference: ${application.reference}")
            Text(
                text = statusLabel(application.status),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(nextStepText(application.status))
        }
    }

    Spacer(modifier = Modifier.height(16.dp))
    Timeline(application)

    Spacer(modifier = Modifier.height(16.dp))
    MetricsCard(application)
}

// AL-8: every status reached so far (with time and reason), then the ones still to come
@Composable
private fun Timeline(application: BorrowerApplication) {
    Text("Progress", style = MaterialTheme.typography.titleMedium)
    Spacer(modifier = Modifier.height(8.dp))

    // Steps already reached: filled dot
    application.timeline.forEach { step ->
        Row(modifier = Modifier.padding(vertical = 4.dp)) {
            Text("●  ")
            Column {
                Text(step.label, fontWeight = FontWeight.Bold)
                val time = formatTime(step.at)
                if (time.isNotEmpty()) Text(time, style = MaterialTheme.typography.bodySmall)
                if (!step.reason.isNullOrBlank()) Text("Reason: ${step.reason}")
            }
        }
    }

    // Steps still to come: empty dot, greyed out
    upcomingStatuses(application.status).forEach { code ->
        Row(modifier = Modifier.padding(vertical = 4.dp)) {
            Text("○  ", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                text = "${statusLabel(code)} (not yet)",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

// AL-7: LTV and DTI from the stored metrics, or "Pending"
@Composable
private fun MetricsCard(application: BorrowerApplication) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Your numbers", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))

            val metrics = application.metrics
            when {
                isPending(application.status) -> Text(PENDING_TEXT)
                metrics == null -> Text("Your numbers aren't available for this application.")
                else -> {
                    MetricRow("LTV", formatPercent(metrics.ltv), checkText(metrics.ltvOk), metrics.ltvOk, LTV_EXPLANATION)
                    Spacer(modifier = Modifier.height(12.dp))
                    MetricRow("DTI", formatPercent(metrics.dti), checkText(metrics.dtiOk), metrics.dtiOk, DTI_EXPLANATION)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))
            // Approval likelihood comes from AL-44 US-405 (Sprint 3); it will be added here then
            Text(
                "Approval likelihood: coming in a later update.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

// One number: name and value, the pass/fail check, and the explanation underneath
@Composable
private fun MetricRow(name: String, value: String, check: String, ok: Boolean?, explanation: String) {
    Text("$name: $value", fontWeight = FontWeight.Bold)
    if (check.isNotEmpty()) {
        // Red when above the limit, the app's main colour when within it
        val colour = if (ok == false) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
        Text(check, color = colour)
    }
    Text(explanation, style = MaterialTheme.typography.bodySmall)
}