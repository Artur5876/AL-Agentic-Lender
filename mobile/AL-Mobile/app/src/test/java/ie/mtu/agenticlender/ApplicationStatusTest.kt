package ie.mtu.agenticlender

import ie.mtu.agenticlender.application.formatTime
import ie.mtu.agenticlender.application.nextStepText
import ie.mtu.agenticlender.application.statusLabel
import ie.mtu.agenticlender.application.upcomingStatuses
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Date
import java.util.TimeZone

// Unit tests for AL-8 US-132 See the lifecycle state of my application
class ApplicationStatusTest {

    @Test
    fun statusCodes_haveTheSameNamesAsTheBackend() {
        assertEquals("Applied", statusLabel("applied"))
        assertEquals("AI Deliberated", statusLabel("ai_deliberated"))
        assertEquals("Underwriter Approved", statusLabel("underwriter_approved"))
    }

    @Test
    fun unknownStatus_isShownAsItIs() {
        assertEquals("something_new", statusLabel("something_new"))
    }

    @Test
    fun applied_hasTheRestOfTheMainPathToCome() {
        assertEquals(
            listOf("ai_deliberated", "underwriter_approved", "funded", "closed"),
            upcomingStatuses("applied")
        )
    }

    @Test
    fun conditionallyApproved_nextIsFullApproval() {
        assertEquals(
            listOf("underwriter_approved", "funded", "closed"),
            upcomingStatuses("conditionally_approved")
        )
    }

    @Test
    fun declinedOrClosed_hasNothingToCome() {
        assertTrue(upcomingStatuses("declined").isEmpty())
        assertTrue(upcomingStatuses("closed").isEmpty())
    }

    @Test
    fun everyStatus_hasANextStepSentence() {
        listOf(
            "applied", "ai_deliberated", "conditionally_approved",
            "underwriter_approved", "funded", "declined", "closed"
        ).forEach { code ->
            assertTrue("No next-step text for $code", nextStepText(code).isNotEmpty())
        }
    }

    @Test
    fun formatTime_showsDayMonthYearAndTime() {
        // 13 Nov 2026 17:58:00 UTC, written as milliseconds since 1970
        val date = Date(1_794_592_680_000L)
        assertEquals("13 Nov 2026, 17:58", formatTime(date, TimeZone.getTimeZone("UTC")))
    }

    @Test
    fun formatTime_isEmptyWhenThereIsNoTime() {
        assertEquals("", formatTime(null))
    }
}