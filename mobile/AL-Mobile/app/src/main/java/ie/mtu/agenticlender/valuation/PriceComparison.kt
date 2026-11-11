package ie.mtu.agenticlender.valuation

import java.util.Locale
import kotlin.math.abs

// AL-6 US-122 Compare asking price with estimate.
// Same rule as the backend calculation module (ai/calc/metrics.py, price_vs_valuation):
// difference = asking price - estimate, and the property is flagged as over-valued
// when the asking price is more than 10% above the estimate.

// 10% over the estimate. Same value as overvaluation_threshold in ai/calc/config.py
const val OVER_VALUATION_THRESHOLD_PERCENT = 10.0

// The result of comparing the asking price with the estimate
data class PriceComparison(
    val differenceEuro: Double,   // positive = asking price is above the estimate
    val differencePercent: Double, // the same difference as a % of the estimate
    val isOverValued: Boolean      // true when more than 10% above the estimate
)

// Compares the asking price with the estimate.
// Returns null if the estimate is 0 or less, because we cannot divide by it.
fun comparePrice(askingPrice: Double, estimate: Double): PriceComparison? {
    if (estimate <= 0.0) {
        return null
    }

    val difference = askingPrice - estimate
    val percent = difference / estimate * 100

    return PriceComparison(
        differenceEuro = difference,
        differencePercent = percent,
        isOverValued = percent > OVER_VALUATION_THRESHOLD_PERCENT
    )
}

// Turns a comparison into one plain-English sentence for the screen, e.g.
// "The asking price is €25,000 (7.1%) above the estimate."
fun describeComparison(comparison: PriceComparison): String {
    // abs() removes the minus sign; the words "above" / "below" say the direction instead
    val euro = String.format(Locale.UK, "€%,.0f", abs(comparison.differenceEuro))
    val percent = String.format(Locale.UK, "%.1f%%", abs(comparison.differencePercent))

    return when {
        comparison.differenceEuro > 0 -> "The asking price is $euro ($percent) above the estimate."
        comparison.differenceEuro < 0 -> "The asking price is $euro ($percent) below the estimate."
        else -> "The asking price matches the estimate."
    }
}