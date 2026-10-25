package ie.mtu.agenticlender.api

data class ValuationRequest(
    val county: String,
    val floorAreaM2: Double,
    val bedrooms: Int,
    val propertyType: String,
    val ber: String
)

data class ValuationResponse(
    val valuationId: String,
    val estimate: Double,
    val low: Double,
    val high: Double,
    val modelVersion: String,
    val isStub: Boolean
)

data class Financials(
    val grossAnnualIncome: Double,
    val monthlyDebts: Double,
    val deposit: Double,
    val loanAmount: Double,
    val termYears: Int
)

data class Property(
    val county: String,
    val floorAreaM2: Double,
    val bedrooms: Int,
    val propertyType: String,
    val ber: String,
    val askingPrice: Double
)

data class ApplicationRequest(
    val buyerType: String,
    val financials: Financials,
    val property: Property,
    val valuationId: String?
)

data class ApplicationResponse(
    val id: String,
    val status: String,
    val statusLabel: String
)