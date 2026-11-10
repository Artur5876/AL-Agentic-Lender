package ie.mtu.agenticlender

import ie.mtu.agenticlender.valuation.comparePrice
import ie.mtu.agenticlender.valuation.describeComparison
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

// Unit tests for AL-6 US-122 Compare asking price with estimate
class PriceComparisonTest {

    @Test
    fun askingPriceAboveEstimate_showsDifferenceInEuroAndPercent() {
        // 350,000 asked for a house estimated at 320,000
        val result = comparePrice(askingPrice = 350_000.0, estimate = 320_000.0)!!

        assertEquals(30_000.0, result.differenceEuro, 0.01)
        assertEquals(9.375, result.differencePercent, 0.001)
        assertEquals("The asking price is €30,000 (9.4%) above the estimate.", describeComparison(result))
    }

    @Test
    fun moreThan10PercentAbove_isFlaggedAsOverValued() {
        val result = comparePrice(askingPrice = 360_000.0, estimate = 320_000.0)!! // 12.5% above
        assertTrue(result.isOverValued)
    }

    @Test
    fun exactly10PercentAbove_isNotFlagged() {
        // The rule is "more than 10%", the same as the backend
        val result = comparePrice(askingPrice = 330_000.0, estimate = 300_000.0)!!
        assertFalse(result.isOverValued)
    }

    @Test
    fun askingPriceBelowEstimate_saysBelow() {
        val result = comparePrice(askingPrice = 290_000.0, estimate = 300_000.0)!!

        assertFalse(result.isOverValued)
        assertEquals("The asking price is €10,000 (3.3%) below the estimate.", describeComparison(result))
    }

    @Test
    fun sameAsEstimate_saysMatches() {
        val result = comparePrice(askingPrice = 300_000.0, estimate = 300_000.0)!!
        assertEquals("The asking price matches the estimate.", describeComparison(result))
    }

    @Test
    fun zeroEstimate_returnsNull() {
        assertNull(comparePrice(askingPrice = 300_000.0, estimate = 0.0))
    }
}