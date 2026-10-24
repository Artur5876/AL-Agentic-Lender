import { auth } from "./firebase";

const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type DecisionOutcome = "underwriter_approved" | "conditionally_approved" | "declined";

/**
 * Change an application's status through the API (docs/api.md, section 3):
 *   POST /applications/{id}/status   body: { "to": "<status>", "reason": "..." }
 *
 * Clients never write applications to Firestore (data model rule 1). The API checks the
 * token, the role and the state machine (backend/app/lifecycle.py), so a wrong move is
 * rejected there: 403 actor_not_allowed, 409 invalid_transition, 422 reason_required.
 * A reason is required for "declined" and "conditionally_approved".
 */
export async function decide(applicationId: string, to: DecisionOutcome, reason?: string) {
  const token = await auth.currentUser?.getIdToken();
  const res = await fetch(`${API_URL}/applications/${encodeURIComponent(applicationId)}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ to, reason }),
  });
  if (!res.ok) {
    // Errors always look like { error: { code, message, details } } (docs/api.md, section 4).
    let message = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (body?.error?.message) message = body.error.message;
    } catch {
      // The body was not JSON; keep the generic message.
    }
    throw new Error(message);
  }
}