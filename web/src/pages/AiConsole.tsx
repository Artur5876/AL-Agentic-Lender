import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth";
import { useDeliberation } from "../hooks/useDeliberation";

const DECISION_LABELS: Record<string, string> = {
  approve: "Approve",
  conditionally_approve: "Conditionally approve",
  decline: "Decline",
};

const AGENT_LABELS: Record<string, string> = {
  affordability: "Affordability agent",
  valuation: "Valuation agent",
  market_research: "Market research agent",
  underwriting_strategist: "Underwriting strategist",
};

const DECISION_COLOURS: Record<string, string> = {
  approve: "bg-green-100 text-green-700",
  conditionally_approve: "bg-amber-100 text-amber-800",
  decline: "bg-red-100 text-red-700",
};

function when(iso?: string) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("en-IE");
}

// Read-only AI console (AL-21 / US-231): one panel per agent, then the final decision and credit memo.
export default function AiConsole() {
  const { id } = useParams();
  const { user, role, logout } = useAuth();
  const { deliberation, steps, loading, error } = useDeliberation(id);

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center justify-between bg-white px-6 py-3 shadow-sm">
        <h1 className="font-semibold text-slate-900">AL Agentic Lender</h1>
        <div className="flex items-center gap-3 text-sm text-slate-600">
          <span>{user?.email}</span>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 capitalize text-indigo-700">{role}</span>
          <button onClick={logout} className="underline">
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-4 p-6">
        <div className="flex gap-4 text-sm">
          <Link to={`/applications/${id}`} className="text-indigo-700 hover:underline">
            ← Back to loan file
          </Link>
          <Link to="/" className="text-indigo-700 hover:underline">
            Queue
          </Link>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-slate-900">AI committee</h2>
          <p className="text-sm text-slate-500">{id} · read-only</p>
        </div>

        {loading && <p className="text-slate-500">Loading…</p>}

        {error && (
          <p className="rounded bg-red-50 p-3 text-sm text-red-700">
            Could not load the AI committee log: {error}
          </p>
        )}

        {!loading && !error && !deliberation && (
          <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">
            The AI committee has not finished for this application yet. This page updates by itself when it does.
          </p>
        )}

        {deliberation?.isStub && (
          <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">
            Placeholder advice: this result comes from the stub committee, not the real AI agents.
          </p>
        )}

        {steps.map((s) => (
          <section key={s.id} className="rounded-xl bg-white p-5 shadow">
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="font-semibold text-slate-900">{AGENT_LABELS[s.agent] ?? s.agent}</h3>
              <div className="text-xs text-slate-500">
                Model: <span className="font-medium text-slate-700">{s.model}</span> · {when(s.timestamp)}
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Output</div>
                <pre className="overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-800">
                  {JSON.stringify(s.output, null, 2)}
                </pre>
              </div>
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Reasoning</div>
                <p className="whitespace-pre-wrap text-sm text-slate-800">{s.reasoning || "—"}</p>
              </div>
            </div>
          </section>
        ))}

        {deliberation && (
          <section className="rounded-xl bg-white p-5 shadow">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Final decision</h3>
              {deliberation.finalDecision && (
                <span
                  className={`rounded-full px-3 py-1 text-sm ${
                    DECISION_COLOURS[deliberation.finalDecision] ?? "bg-slate-200 text-slate-700"
                  }`}
                >
                  {DECISION_LABELS[deliberation.finalDecision] ?? deliberation.finalDecision}
                </span>
              )}
            </div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Credit memo</div>
            <p className="whitespace-pre-wrap text-sm text-slate-800">{deliberation.creditMemo || "—"}</p>
            {deliberation.completedAt && (
              <p className="mt-3 text-xs text-slate-400">
                Completed {deliberation.completedAt.toDate().toLocaleString("en-IE")}
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
