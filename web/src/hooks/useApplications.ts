import { useEffect, useState } from "react";
import { collection, onSnapshot, orderBy, query, where } from "firebase/firestore";
import { db } from "../firebase";
import type { Application, Role } from "../types";

/**
 * Live list of applications (AL-17).
 * The query MUST match the security rules (data model section 4):
 *  - broker: where brokerId == myUid   (the `where` is required, or Firestore rejects it)
 *  - underwriter: everything
 */
export function useApplications(role: Role | null, uid: string | undefined) {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!role || !uid) return;
    const col = collection(db, "applications");
    const q =
      role === "broker"
        ? query(col, where("brokerId", "==", uid), orderBy("updatedAt", "desc"))
        : query(col, orderBy("updatedAt", "desc"));

    // onSnapshot pushes every change; returning the unsubscribe function cleans up.
    return onSnapshot(
      q,
      (snap) => {
        setApps(snap.docs.map((d) => ({ ...(d.data() as Omit<Application, "id">), id: d.id })));
        setError(null);
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
    );
  }, [role, uid]);

  return { apps, loading, error };
}
