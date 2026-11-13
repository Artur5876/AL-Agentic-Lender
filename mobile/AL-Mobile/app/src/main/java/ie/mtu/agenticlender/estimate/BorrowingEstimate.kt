package ie.mtu.agenticlender.estimate

import java.util.Locale

// AL-3 US-111 Enter income, debts, deposit and term for borrowing estimate.
// Plain Kotlin only (no Android), so it can be unit tested on its own.
// The numbers are NOT worked out here: the backend's calculation module does that
// (POST /affordability). This file only checks the inputs and formats the answer.

// Shown under every estimate (acceptance criteria: "'Indicative only' note shown")
const val INDICATIVE_NOTE =
    "Indicative only. This is an estimate based on the details you entered, not a loan offer."

// Checks the four numbers and the buyer type before anything is sent.
// Returns the first problem as a sentence, or null if everything is fine.
// Rules from the acceptance criteria: amounts can't be negative, term is 5 to 35 years.
fun validateEstimateInputs(
    buyerType: String,
    income: Double?,
    monthlyDebts: Double?,
    deposit: Double?,
    termYears: Int?
): String? {
    return when {
        buyerType.isBlank() -> "Please choose first-time or subsequent buyer."
        income == null || !income.isFinite() || income < 0.0 -> "Gross annual income must be 0 or more."
        monthlyDebts == null || !monthlyDebts.isFinite() || monthlyDebts < 0.0 -> "Monthly debts must be 0 or more."
        deposit == null || !deposit.isFinite() || deposit < 0.0 -> "Deposit must be 0 or more."
        termYears == null || termYears !in 5..35 -> "Mortgage term must be between 5 and 35 years."
        else -> null
    }
}

// 380000.0 -> "€380,000"
fun formatEuro(amount: Double): String = String.format(Locale.UK, "€%,.0f", amount)

// 1814.18 -> "€1,814.18" (repayments keep the cents)
fun formatEuroWithCents(amount: Double): String = String.format(Locale.UK, "€%,.2f", amount)

// 4.0 -> "4.0 times your income"; null -> "Not available"
fun formatLti(lti: Double?): String {
    if (lti == null) return "Not available"
    return String.format(Locale.UK, "%.1f times your income", lti)
}

// 0.8636 -> "86.4%"; null -> "Not available"
fun formatFraction(fraction: Double?): String {
    if (fraction == null) return "Not available"
    return String.format(Locale.UK, "%.1f%%", fraction * 100)
}

// Explains WHY the maximum loan is what it is, from the "limitedBy" the backend sends back
fun limitedByText(limitedBy: String): String {
    return when (limitedBy) {
        "lti" -> "Limited by your income: lenders can only lend a set multiple of your gross income."
        "deposit" -> "Limited by your deposit: you need a deposit of at least 10% of the property price."
        else -> ""
    }
}