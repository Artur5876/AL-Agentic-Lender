package ie.mtu.agenticlender

import ie.mtu.agenticlender.application.checkText
import ie.mtu.agenticlender.application.formatPercent
import ie.mtu.agenticlender.application.isPending
import ie.mtu.agenticlender.application.metricsFromMap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

// Unit tests for AL-7 US-131 See LTV, DTI and approval likelihood
class ApplicationMetricsTest {

    @Test
    fun readsTheStoredMetrics_likeTheBackendSavesThem() {
        // The same shape as applications/{id}.metrics in docs/data-model.md
        val stored = mapOf(
            "lti" to 3.8,
            "ltv" to 0.85,
            "dti" to 0.3214,
            "stressedDti" to 0.3702,
            "monthlyRepayment" to 1432.86,
            "checks" to mapOf("ltiOk" to true, "ltvOk" to true, "dtiOk" to true, "stressedDtiOk" to true)
        )

        val metrics = metricsFromMap(stored)!!

        assertEquals(0.85, metrics.ltv!!, 0.0001)
        assertEquals(0.3214, metrics.dti!!, 0.0001)
        assertEquals(true, metrics.ltvOk)
        assertEquals(true, metrics.dtiOk)
    }

    @Test
    fun wholeNumbersFromFirestore_areReadToo() {
        // Firestore gives back 1 (not 1.0) as a Long
        val metrics = metricsFromMap(mapOf("ltv" to 1L, "dti" to null))!!
        assertEquals(1.0, metrics.ltv!!, 0.0001)
        assertNull(metrics.dti)
    }

    @Test
    fun noMetrics_givesNull() {
        assertNull(metricsFromMap(null))
    }

    @Test
    fun formatPercent_turnsAFractionIntoAPercentage() {
        assertEquals("85.0%", formatPercent(0.85))
        assertEquals("32.1%", formatPercent(0.3214))
        assertEquals("Not available", formatPercent(null))
    }

    @Test
    fun checkText_saysWithinOrAboveTheLimit() {
        assertEquals("Within the limit", checkText(true))
        assertEquals("Above the limit", checkText(false))
        assertEquals("", checkText(null))
    }

    @Test
    fun numbersArePending_untilTheAiCommitteeHasFinished() {
        assertTrue(isPending("applied"))
        assertFalse(isPending("ai_deliberated"))
        assertFalse(isPending("underwriter_approved"))
    }
}