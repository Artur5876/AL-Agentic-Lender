package ie.mtu.agenticlender.api

// AL-3 US-111: what the app sends to, and gets back from, POST /affordability (docs/api.md).

// The borrower's details. buyerType is "first_time" or "subsequent".
data class AffordabilityRequest(
    val buyerType: String,
    val grossAnnualIncome: Double,
    val monthlyDebts: Double,
    val deposit: Double,
    val termYears: Int
)

// The estimate, worked out by the backend's calculation module (US-410). Nothing is saved.
// lti, ltv and dti are fractions (0.8636 = 86.36%) and can be null, e.g. when income is 0.
data class AffordabilityResponse(
    val maxLoan: Double,          // the most the borrower may be able to borrow, in euro
    val limitedBy: String,        // "lti" (limited by income) or "deposit" (limited by deposit)
    val lti: Double?,             // loan-to-income, e.g. 4.0 = 4 times income
    val ltv: Double?,             // loan-to-value
    val monthlyRepayment: Double, // euro per month for maxLoan over the chosen term
    val dti: Double?,             // debt-to-income
    val indicativeOnly: Boolean   // always true: it's an estimate, not an offer
)