import { useEffect, useState } from "react";
import { doc, onSnapshot } from "firebase/firestore";
import { db } from "../firebase";
import type { Application } from "../types";

/**
 * Live single application (AL-19). Reads Firestore directly, like the queue does.
 * The security rules (canReadApp) decide who may read it: an underwriter any file, a broker
 * only their own. A file you may not see comes back as a permission error, shown as "not found".
 */
export function useApplication(id: string | undefined) {
  const [app, setApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    return onSnapshot(
      doc(db, "applications", id),
      (snap) => {
        setApp(snap.exists() ? { ...(snap.data() as Omit<Application, "id">), id: snap.id } : null);
        setError(null);
        setLoading(false);
      },
      (err) => {
        setApp(null);
        setError(err.message);
        setLoading(false);
      },
    );
  }, [id]);

  return { app, loading, error };
}
