import { useEffect, useState } from "react";
import { collection, doc, onSnapshot } from "firebase/firestore";
import { db } from "../firebase";

// Shapes follow docs/data-model.md section 2.4 (deliberations/{applicationId} and its steps).
export interface DeliberationStep {
  id: string; // 01-affordability, 02-valuation, 03-market_research, 04-underwriting_strategist
  agent: string;
  model: string;
  output: Record<string, unknown>;
  reasoning: string;
  timestamp: string; // ISO 8601, UTC
}

export interface Deliberation {
  status?: string;
  finalDecision?: "approve" | "conditionally_approve" | "decline";
  creditMemo?: string;
  isStub?: boolean;
  completedAt?: { toDate(): Date } | null;
}

/**
 * Live AI committee log for one application (AL-21, read-only).
 * The rules allow staff who can read the application; the backend is the only writer.
 * deliberation is null until the committee has finished (application still "applied").
 */
export function useDeliberation(id: string | undefined) {
  const [deliberation, setDeliberation] = useState<Deliberation | null>(null);
  const [steps, setSteps] = useState<DeliberationStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const unsubDoc = onSnapshot(
      doc(db, "deliberations", id),
      (snap) => {
        setDeliberation(snap.exists() ? (snap.data() as Deliberation) : null);
        setError(null);
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
    );
    const unsubSteps = onSnapshot(
      collection(db, "deliberations", id, "steps"),
      (snap) => {
        // The step IDs start with 01-, 02-, ... so sorting by ID gives the order the agents ran in.
        const rows = snap.docs.map((d) => ({ ...(d.data() as Omit<DeliberationStep, "id">), id: d.id }));
        rows.sort((a, b) => a.id.localeCompare(b.id));
        setSteps(rows);
      },
      (err) => setError(err.message),
    );
    return () => {
      unsubDoc();
      unsubSteps();
    };
  }, [id]);

  return { deliberation, steps, loading, error };
}
