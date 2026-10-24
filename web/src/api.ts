import { auth } from "./firebase";

const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type DecisionOutcome = "underwriter_approved" | "conditionally_approved" | "declined";

/**
 * Clients never write applications to Firestore: changes go through the Python API
 * (data model rule 1). The API checks the ID token and the role itself.
 *
 * TODO: the URL and body below are a GUESS. Check docs/api.md (or http://localhost:8000/docs)
 * and change them to match the real endpoint.
 */
export async function decide(applicationId: string, outcome: DecisionOutcome, reason?: string) {
  const token = await auth.currentUser?.getIdToken();
  const res = await fetch(`${API_URL}/applications/${applicationId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ outcome, reason }),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
}
