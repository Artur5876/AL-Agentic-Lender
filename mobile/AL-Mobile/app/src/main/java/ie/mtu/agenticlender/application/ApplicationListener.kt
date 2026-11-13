package ie.mtu.agenticlender.application

import com.google.firebase.Timestamp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.DocumentSnapshot
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.ListenerRegistration
import com.google.firebase.firestore.Query

// AL-8 US-132 and AL-7 US-131: listen to the borrower's latest application in Firestore,
// so the screen updates by itself whenever the status changes (no refresh button needed).
// This is the query from docs/data-model.md section 4 for borrowers.

// Everything the "My application" screen needs from one application document
data class BorrowerApplication(
    val reference: String,          // e.g. "AL-2026-0117" (the document ID)
    val status: String,             // current status code, e.g. "applied"
    val timeline: List<StatusStep>, // every status it has been in, oldest first
    val metrics: ApplicationMetrics?
)

// Starts listening. onChange is called straight away, then again on every change.
// onChange(null) means the borrower has no application yet.
// Returns the listener, so the screen can stop it (registration.remove()) when it closes.
fun listenToLatestApplication(
    onChange: (BorrowerApplication?) -> Unit,
    onError: (String) -> Unit
): ListenerRegistration? {
    val uid = FirebaseAuth.getInstance().currentUser?.uid
    if (uid == null) {
        onError("You're not logged in. Please log in again.")
        return null
    }

    return FirebaseFirestore.getInstance()
        .collection("applications")
        .whereEqualTo("borrowerId", uid)                     // only my applications (security rules require this)
        .orderBy("createdAt", Query.Direction.DESCENDING)    // newest first
        .limit(1)                                            // just the latest one
        .addSnapshotListener { snapshot, error ->
            if (error != null) {
                onError("Couldn't load your application: ${error.message}")
                return@addSnapshotListener
            }
            val document = snapshot?.documents?.firstOrNull()
            onChange(document?.let { toMyApplication(it) })
        }
}

// Turns a Firestore document into a BorrowerApplication
private fun toMyApplication(document: DocumentSnapshot): BorrowerApplication {
    // statusHistory is a list of maps: {status, at, by, role, reason}
    val history = (document.get("statusHistory") as? List<*>).orEmpty()
        .mapNotNull { it as? Map<*, *> }
        .map { entry ->
            val code = entry["status"] as? String ?: ""
            StatusStep(
                status = code,
                label = statusLabel(code),
                at = (entry["at"] as? Timestamp)?.toDate(), // Firestore time -> Java Date
                reason = entry["reason"] as? String
            )
        }

    return BorrowerApplication(
        reference = document.id,
        status = document.getString("status") ?: "",
        timeline = history,
        metrics = metricsFromMap(document.get("metrics") as? Map<*, *>)
    )
}