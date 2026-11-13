package ie.mtu.agenticlender

import ie.mtu.agenticlender.estimate.INDICATIVE_NOTE
import ie.mtu.agenticlender.estimate.formatEuro
import ie.mtu.agenticlender.estimate.formatEuroWithCents
import ie.mtu.agenticlender.estimate.formatFraction
import ie.mtu.agenticlender.estimate.formatLti
import ie.mtu.agenticlender.estimate.limitedByText
import ie.mtu.agenticlender.estimate.validateEstimateInputs
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

// Unit tests for AL-3 US-111 Enter income, debts, deposit and term for borrowing estimate
class BorrowingEstimateTest {

    // ---- Checking the inputs (acceptance criteria: non-negative amounts, term 5-35, buyer type chosen)

    @Test
    fun validInputs_haveNoProblem() {
        assertNull(validateEstimateInputs("first_time", 95_000.0, 300.0, 60_000.0, 30))
    }

    @Test
    fun zeroAmounts_areAllowed() {
        // "Non-negative" means 0 is fine (e.g. no existing debts)
        assertNull(validateEstimateInputs("subsequent", 0.0, 0.0, 0.0, 25))
    }

    @Test
    fun buyerTypeMustBeChosen() {
        assertEquals(
            "Please choose first-time or subsequent buyer.",
            validateEstimateInputs("", 95_000.0, 300.0, 60_000.0, 30)
        )
    }

    @Test
    fun negativeAmounts_areRejected() {
        assertEquals("Gross annual income must be 0 or more.", validateEstimateInputs("first_time", -1.0, 0.0, 0.0, 30))
        assertEquals("Monthly debts must be 0 or more.", validateEstimateInputs("first_time", 1.0, -5.0, 0.0, 30))
        assertEquals("Deposit must be 0 or more.", validateEstimateInputs("first_time", 1.0, 0.0, -10.0, 30))
    }

    @Test
    fun blankOrNotANumber_isRejected() {
        // The screen turns text into numbers with toDoubleOrNull(), which gives null for "" or "abc"
        assertEquals("Gross annual income must be 0 or more.", validateEstimateInputs("first_time", null, 0.0, 0.0, 30))
    }

    @Test
    fun termMustBeBetween5And35Years() {
        val message = "Mortgage term must be between 5 and 35 years."
        assertEquals(message, validateEstimateInputs("first_time", 1.0, 0.0, 0.0, 4))
        assertEquals(message, validateEstimateInputs("first_time", 1.0, 0.0, 0.0, 36))
        assertEquals(message, validateEstimateInputs("first_time", 1.0, 0.0, 0.0, null))
        assertNull(validateEstimateInputs("first_time", 1.0, 0.0, 0.0, 5))
        assertNull(validateEstimateInputs("first_time", 1.0, 0.0, 0.0, 35))
    }

    // ---- Showing the answer (example numbers from docs/api.md)

    @Test
    fun euroAmounts_areFormattedWithCommas() {
        assertEquals("€380,000", formatEuro(380_000.0))
        assertEquals("€1,814.18", formatEuroWithCents(1814.18))
    }

    @Test
    fun ltiAndLtv_areFormatted() {
        assertEquals("4.0 times your income", formatLti(4.0))
        assertEquals("86.4%", formatFraction(0.8636))
        assertEquals("Not available", formatLti(null))
        assertEquals("Not available", formatFraction(null))
    }

    @Test
    fun limitedBy_explainsWhy() {
        assertTrue(limitedByText("lti").startsWith("Limited by your income"))
        assertTrue(limitedByText("deposit").startsWith("Limited by your deposit"))
        assertEquals("", limitedByText("something_else"))
    }

    @Test
    fun indicativeNote_saysItIsNotAnOffer() {
        assertTrue(INDICATIVE_NOTE.contains("Indicative only"))
        assertTrue(INDICATIVE_NOTE.contains("not a loan offer"))
    }
}