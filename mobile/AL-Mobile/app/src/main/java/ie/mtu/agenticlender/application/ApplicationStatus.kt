package ie.mtu.agenticlender.application

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

// AL-8 US-132 See the lifecycle state of my application.
// Plain Kotlin only (no Android or Firebase), so it can be unit tested on its own.

// Status codes and their names, the same as LABELS in backend/app/lifecycle.py
val STATUS_LABELS = mapOf(
    "applied" to "Applied",
    "ai_deliberated" to "AI Deliberated",
    "conditionally_approved" to "Conditionally Approved",
    "underwriter_approved" to "Underwriter Approved",
    "funded" to "Funded",
    "declined" to "Declined",
    "closed" to "Closed"
)

// The normal path an application takes, in order (backend/app/lifecycle.py TRANSITIONS)
val MAIN_PATH = listOf("applied", "ai_deliberated", "underwriter_approved", "funded", "closed")

// One step in the timeline: a status the application has reached, and when
data class StatusStep(
    val status: String,   // code, e.g. "ai_deliberated"
    val label: String,    // name to show, e.g. "AI Deliberated"
    val at: Date?,        // when it moved to this status
    val reason: String?   // only for declined / conditionally approved
)

// Turns a status code into its name. Unknown codes are shown as they are.
fun statusLabel(code: String): String = STATUS_LABELS[code] ?: code

// The statuses still to come after the current one, so the borrower can see what's left.
// A declined or closed application has nothing left.
fun upcomingStatuses(current: String): List<String> {
    return when (current) {
        "declined", "closed" -> emptyList()
        // After a conditional approval the next step is full approval, then the rest of the path
        "conditionally_approved" -> listOf("underwriter_approved", "funded", "closed")
        else -> {
            val index = MAIN_PATH.indexOf(current)
            if (index == -1) emptyList() else MAIN_PATH.drop(index + 1)
        }
    }
}

// A plain-language sentence telling the borrower what happens next
fun nextStepText(status: String): String {
    return when (status) {
        "applied" -> "Our AI committee is reviewing your application. This usually takes a few minutes."
        "ai_deliberated" -> "The AI review is done. An underwriter will now look at it and make a decision."
        "conditionally_approved" -> "You've been approved with conditions. The underwriter will confirm once they're met."
        "underwriter_approved" -> "Approved! Your digital loan note has been created. The next step is funding."
        "funded" -> "Your loan has been paid out."
        "declined" -> "Your application was declined. The reason is shown in the timeline."
        "closed" -> "This application is closed."
        else -> ""
    }
}

// Formats a time for the timeline, e.g. "13 Nov 2026, 17:58". Empty text if there's no time.
// timeZone can be set in tests so the result is always the same.
fun formatTime(date: Date?, timeZone: TimeZone = TimeZone.getDefault()): String {
    if (date == null) return ""
    val formatter = SimpleDateFormat("d MMM yyyy, HH:mm", Locale.UK)
    formatter.timeZone = timeZone
    return formatter.format(date)
}