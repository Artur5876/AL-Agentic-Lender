import { useMemo, useState } from "react";
import { useAuth } from "../auth";
import { useApplications } from "../hooks/useApplications";
import { decide, type DecisionOutcome } from "../api";
import {
  LTV_BAND_LABELS,
  RISK_TIERS,
  STATUSES,
  STATUS_LABELS,
  ltvBand,
  type Application,
  type LtvBand,
  type RiskTier,
  type Status,
} from "../types";

const euro = new Intl.NumberFormat("en-IE", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

// Statuses where an underwriter can still make a decision (see lifecycle table in the data model).
const DECIDABLE: Status[] = ["ai_deliberated", "conditionally_approved"];

export default function Queue() {
  const { user, role, logout } = useAuth();
  const { apps, loading, error } = useApplications(role, user?.uid);

  // AL-18 filters
  const [status, setStatus] = useState<Status | "all">("all");
  const [band, setBand] = useState<LtvBand | "all">("all");
  const [risk, setRisk] = useState<RiskTier | "none" | "all">("all");
  const [actionError, setActionError] = useState<string | null>(null);

  const rows = useMemo(
    () =>
      apps.filter((a) => {
        if (status !== "all" && a.status !== status) return false;
        if (band !== "all" && ltvBand(a.metrics?.ltv) !== band) return false;
        if (risk !== "all" && (a.riskTier ?? "none") !== risk) return false;
        return true;
      }),
    [apps, status, band, risk],
  );

  async function onDecide(app: Application, outcome: DecisionOutcome) {
    let reason: string | undefined;
    if (outcome !== "underwriter_approved") {
      // US-252: declining / conditionally approving needs a written reason.
      const typed = window.prompt("Reason (required):");
      if (!typed || !typed.trim()) return;
      reason = typed.trim();
    }
    setActionError(null);
    try {
      await decide(app.id, outcome, reason);
      // No manual refresh needed: the live listener picks up the change.
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not save the decision.");
    }
  }

  const selectClass = "rounded border border-slate-300 bg-white px-2 py-1 text-sm";

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center justify-between bg-white px-6 py-3 shadow-sm">
        <h1 className="font-semibold text-slate-900">AL Agentic Lender</h1>
        <div className="flex items-center gap-3 text-sm text-slate-600">
          <span>{user?.email}</span>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-indigo-700 capitalize">{role}</span>
          <button onClick={logout} className="underline">
            Sign out
          </button>
        </div>
      </header>

      <main className="p-6 space-y-4">
        <div className="flex flex-wrap items-end gap-4">
          <h2 className="text-lg font-semibold text-slate-900 mr-auto">Application queue</h2>
          <label className="text-xs text-slate-500">
            Status
            <select
              className={`${selectClass} block`}
              value={status}
              onChange={(e) => setStatus(e.target.value as Status | "all")}
            >
              <option value="all">All</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-500">
            LTV band
            <select
              className={`${selectClass} block`}
              value={band}
              onChange={(e) => setBand(e.target.value as LtvBand | "all")}
            >
              <option value="all">All</option>
              {(Object.keys(LTV_BAND_LABELS) as LtvBand[]).map((b) => (
                <option key={b} value={b}>
                  {LTV_BAND_LABELS[b]}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-500">
            Risk tier
            <select
              className={`${selectClass} block`}
              value={risk}
              onChange={(e) => setRisk(e.target.value as RiskTier | "none" | "all")}
            >
              <option value="all">All</option>
              {RISK_TIERS.map((r) => (
                <option key={r} value={r} className="capitalize">
                  {r}
                </option>
              ))}
              <option value="none">Not set</option>
            </select>
          </label>
        </div>

        {error && (
          <p className="rounded bg-red-50 p-3 text-sm text-red-700">
            Could not load applications: {error}
          </p>
        )}
        {actionError && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{actionError}</p>}

        <div className="overflow-x-auto rounded-xl bg-white shadow">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Applicant</th>
                <th className="px-4 py-3">Property</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">LTV</th>
                <th className="px-4 py-3">Risk tier</th>
                <th className="px-4 py-3">Status</th>
                {role === "underwriter" && <th className="px-4 py-3">Decision</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td className="px-4 py-6 text-slate-500" colSpan={7}>
                    Loading…
                  </td>
                </tr>
              )}
              {!loading && rows.length === 0 && (
                <tr>
                  <td className="px-4 py-6 text-slate-500" colSpan={7}>
                    No applications to show.
                  </td>
                </tr>
              )}
              {rows.map((a) => {
                const ltv = a.metrics?.ltv;
                return (
                  <tr key={a.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{a.borrowerName}</div>
                      <div className="text-xs text-slate-500">{a.id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="capitalize">
                        {(a.property?.propertyType ?? "—").replace("_", " ")}
                        {a.property?.county ? `, ${a.property.county}` : ""}
                      </div>
                      <div className="text-xs text-slate-500">
                        {a.property?.askingPrice != null ? `Asking ${euro.format(a.property.askingPrice)}` : ""}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {a.financials?.loanAmount != null ? euro.format(a.financials.loanAmount) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {/* ltv is a fraction: 0.882 -> 88.2% */}
                      {ltv != null ? `${(ltv * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 capitalize">{a.riskTier ?? "—"}</td>
                    <td className="px-4 py-3">{STATUS_LABELS[a.status] ?? a.status}</td>
                    {role === "underwriter" && (
                      <td className="px-4 py-3">
                        {DECIDABLE.includes(a.status) && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => onDecide(a, "underwriter_approved")}
                              className="rounded bg-green-600 px-2 py-1 text-xs text-white"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => onDecide(a, "declined")}
                              className="rounded bg-red-600 px-2 py-1 text-xs text-white"
                            >
                              Decline
                            </button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-slate-500">
          Showing {rows.length} of {apps.length}. LTV and risk tier show “—” until the backend fills them in.
        </p>
      </main>
    </div>
  );
}
