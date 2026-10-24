import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";

/** AL-14: only signed-in brokers and underwriters get through. Borrowers go to /no-access. */
export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { loading, user, role } = useAuth();
  if (loading) return <p className="p-8 text-slate-500">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!role) return <Navigate to="/no-access" replace />;
  return <>{children}</>;
}
