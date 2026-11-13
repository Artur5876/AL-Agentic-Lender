package ie.mtu.agenticlender.application

import java.util.Locale

// AL-7 US-131 See LTV, DTI and approval likelihood.
// Plain Kotlin only, so it can be unit tested on its own.
// The numbers are NOT worked out here: the backend's calculation module (US-410) works them
// out when the application is submitted and stores them in applications/{id}.metrics.
// This file only reads and formats them, so the app always shows the stored values.

// The numbers for one application. LTV and DTI are stored as fractions, e.g. 0.85 = 85%.
data class ApplicationMetrics(
    val ltv: Double?,
    val dti: Double?,
    val ltvOk: Boolean?,   // true = within the limit, false = above it, null = not checked
    val dtiOk: Boolean?
)

// One-line explanations shown under each number
const val LTV_EXPLANATION =
    "Loan-to-value: how much of the property's value you're borrowing. Lower is safer."
const val DTI_EXPLANATION =
    "Debt-to-income: how much of your monthly income goes on the mortgage and other debts. Lower is safer."

// Shown instead of the numbers until the AI committee has finished
const val PENDING_TEXT = "Pending. Your numbers appear once the AI committee has reviewed your application."

// The numbers are shown only once the AI committee has finished,
// i.e. when the application has moved past "applied"
fun isPending(status: String): Boolean = status == "applied"

// 0.8512 -> "85.1%". null (e.g. income was 0) -> "Not available"
fun formatPercent(fraction: Double?): String {
    if (fraction == null) return "Not available"
    return String.format(Locale.UK, "%.1f%%", fraction * 100)
}

// Text for the pass/fail check next to each number
fun checkText(ok: Boolean?): String {
    return when (ok) {
        true -> "Within the limit"
        false -> "Above the limit"
        null -> ""
    }
}

// Reads the "metrics" map from the Firestore document.
// Firestore can give numbers back as Long (whole numbers) or Double, so "as? Number" handles both.
// Returns null if the application has no metrics.
fun metricsFromMap(map: Map<*, *>?): ApplicationMetrics? {
    if (map == null) return null
    val checks = map["checks"] as? Map<*, *>
    return ApplicationMetrics(
        ltv = (map["ltv"] as? Number)?.toDouble(),
        dti = (map["dti"] as? Number)?.toDouble(),
        ltvOk = checks?.get("ltvOk") as? Boolean,
        dtiOk = checks?.get("dtiOk") as? Boolean
    )
}