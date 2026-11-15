import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth";
import { useApplication } from "../hooks/useApplication";
import { STATUS_LABELS } from "../types";
import { OVER_VALUATION_THRESHOLD, comparePrice } from "../valuation";

const euro0 = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const euro2 = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 });

const money0 = (n?: number | null) => (n == null ? "—" : euro0.format(n));
const money2 = (n?: number | null) => (n == null ? "—" : euro2.format(n));
// Ratios are fractions: 0.2671 -> 26.7%
const pct = (n?: number | null) => (n == null ? "—" : `${(n * 100).toFixed(1)}%`);
const signedPct = (n: number) => `${n > 0 ? "+" : ""}${(n * 100).toFixed(1)}%`;
const times = (n?: number | null) => (n == null ? "—" : `${n.toFixed(2)}×`);

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className={`break-all text-right ${bold ? "font-semibold text-slate-900" : "text-slate-900"}`}>{value}</dd>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl bg-white p-5 shadow">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      {children}
    </section>
  );
}

// A calculation-module check: true = pass, false = fail, undefined = not run (seed data).
function Check({ ok }: { ok?: boolean }) {
  if (ok === undefined) return <span className="text-slate-400">not checked</span>;
  return ok ? (
    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">Pass</span>
  ) : (
    <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">Fail</span>
  );
}

function Metric({ label, value, check, hint }: { label: string; value: string; check?: boolean; hint: string }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-xl font-semibold text-slate-900">{value}</div>
      <div className="mt-1 flex items-center justify-between text-xs text-slate-400">
        <span>{hint}</span>
        <Check ok={check} />
      </div>
    </div>
  );
}

export default function LoanFile() {
  const { id } = useParams();
  const { user, role, logout } = useAuth();
  const { app, loading, error } = useApplication(id);

  const f = app?.financials;
  const m = app?.metrics ?? null;
  const p = app?.property;
  const v = app?.valuation ?? null;
  const price = comparePrice(p?.askingPrice, v?.estimate);

  // Monthly income is shown only so the DTI breakdown can be read; the DTI itself comes from US-410.
  const monthlyIncome = f?.grossAnnualIncome != null ? f.grossAnnualIncome / 12 : null;

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
        <Link to="/" className="text-sm text-indigo-700 hover:underline">
          ← Back to queue
        </Link>
        {id && (
          <Link to={`/applications/${id}/ai`} className="ml-4 text-sm text-indigo-700 hover:underline">
            AI committee →
          </Link>
        )}

        {loading && <p className="text-slate-500">Loading…</p>}

        {!loading && (error || !app) && (
          <p className="rounded bg-red-50 p-3 text-sm text-red-700">
            Loan file not found, or you do not have access to it.
          </p>
        )}

        {app && (
          <>
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">{app.borrowerName}</h2>
                <p className="text-sm text-slate-500">
                  {app.reference ?? app.id}
                  {app.buyerType ? ` · ${app.buyerType === "first_time" ? "First-time buyer" : "Subsequent buyer"}` : ""}
                </p>
              </div>
              <span className="rounded-full bg-slate-200 px-3 py-1 text-sm text-slate-700">
                {STATUS_LABELS[app.status] ?? app.status}
              </span>
            </div>

            {!m && (
              <p className="rounded bg-amber-50 p-3 text-sm text-amber-800">
                Calculation metrics are not available for this file yet.
              </p>
            )}

            <Card title="Affordability (calculation module, US-410)">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Metric label="LTI" value={times(m?.lti)} check={m?.checks?.ltiOk} hint="Loan ÷ income" />
                <Metric label="DTI" value={pct(m?.dti)} check={m?.checks?.dtiOk} hint="Debt ÷ income" />
                <Metric
                  label="Stress-tested DTI"
                  value={pct(m?.stressedDti)}
                  check={m?.checks?.stressedDtiOk}
                  hint="At a higher rate"
                />
                <Metric
                  label="Monthly repayment"
                  value={money2(m?.monthlyRepayment)}
                  hint={f?.termYears ? `Over ${f.termYears} years` : ""}
                />
              </div>
              <p className="mt-3 text-xs text-slate-400">
                LTI, DTI and repayment come from the calculation module; this page only displays them.
              </p>
            </Card>

            <Card title="Asking price vs ML valuation">
              <div className="grid gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-slate-200 p-3">
                  <div className="text-xs text-slate-500">Asking price</div>
                  <div className="text-xl font-semibold text-slate-900">{money0(p?.askingPrice)}</div>
                </div>
                <div className="rounded-lg border border-slate-200 p-3">
                  <div className="text-xs text-slate-500">ML estimate</div>
                  <div className="text-xl font-semibold text-slate-900">{money0(v?.estimate)}</div>
                </div>
                <div className="rounded-lg border border-slate-200 p-3">
                  <div className="text-xs text-slate-500">Difference</div>
                  <div className="text-xl font-semibold text-slate-900">
                    {price ? `${price.differenceEuro > 0 ? "+" : ""}${euro0.format(price.differenceEuro)}` : "—"}
                  </div>
                </div>
                <div
                  className={`rounded-lg border p-3 ${
                    price?.isOverValued ? "border-red-300 bg-red-50" : "border-slate-200"
                  }`}
                >
                  <div className="text-xs text-slate-500">Variance</div>
                  <div className="text-xl font-semibold text-slate-900">{price ? signedPct(price.variance) : "—"}</div>
                  {price && (
                    <div className="mt-1 text-xs">
                      {price.isOverValued ? (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-red-700">Over-valued</span>
                      ) : (
                        <span className="rounded-full bg-green-100 px-2 py-0.5 text-green-700">Within range</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-400">
                Flagged when the asking price is more than {OVER_VALUATION_THRESHOLD * 100}% above the estimate (same
                rule as mobile and the calculation module).
                {price == null && " No comparison is possible until a valuation is stored for this file."}
              </p>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card title="Income and debts">
                <dl className="divide-y divide-slate-100">
                  <Row label="Gross annual income" value={money0(f?.grossAnnualIncome)} />
                  <Row label="Gross monthly income" value={money2(monthlyIncome)} />
                  <Row label="Existing monthly debts" value={money2(f?.monthlyDebts)} />
                  <Row label="New monthly repayment" value={money2(m?.monthlyRepayment)} />
                  <Row label="DTI (debts + new repayment) ÷ income" value={pct(m?.dti)} bold />
                  <Row label="Stress-tested DTI" value={pct(m?.stressedDti)} bold />
                </dl>
              </Card>

              <Card title="Loan">
                <dl className="divide-y divide-slate-100">
                  <Row label="Loan amount" value={money0(f?.loanAmount)} />
                  <Row label="Deposit" value={money0(f?.deposit)} />
                  <Row label="Term" value={f?.termYears != null ? `${f.termYears} years` : "—"} />
                  <Row label="LTV" value={pct(m?.ltv)} bold />
                  <Row label="LTV check" value={m?.checks?.ltvOk == null ? "not checked" : m.checks.ltvOk ? "Pass" : "Fail"} />
                </dl>
              </Card>

              <Card title="Property">
                <dl className="divide-y divide-slate-100">
                  <Row label="Type" value={(p?.propertyType ?? "—").replace("_", " ")} />
                  <Row label="County" value={p?.county ?? "—"} />
                  <Row label="Floor area" value={p?.floorAreaM2 != null ? `${p.floorAreaM2} m²` : "—"} />
                  <Row label="Bedrooms" value={p?.bedrooms != null ? String(p.bedrooms) : "—"} />
                  <Row label="BER" value={p?.ber ?? "—"} />
                  <Row label="Asking price" value={money0(p?.askingPrice)} />
                </dl>
              </Card>

              <Card title="Valuation">
                <dl className="divide-y divide-slate-100">
                  <Row label="Estimate" value={money0(v?.estimate)} />
                  <Row label="Range (80%)" value={v?.low != null && v?.high != null ? `${money0(v.low)} – ${money0(v.high)}` : "—"} />
                  <Row label="Model" value={v?.modelVersion ?? "—"} />
                </dl>
              </Card>
            </div>
            {(app.decision || app.loanNote) && (
              <Card title="Decision and loan note">
                <dl className="divide-y divide-slate-100">
                  {app.decision && (
                    <>
                      <Row
                        label="Decision"
                        value={app.decision.outcome ? (STATUS_LABELS[app.decision.outcome] ?? app.decision.outcome) : "—"}
                        bold
                      />
                      <Row label="Reason" value={app.decision.reason ?? "—"} />
                      <Row label="Decided by" value={app.decision.by ?? "—"} />
                      <Row label="Decided at" value={app.decision.at ? app.decision.at.toDate().toLocaleString("en-IE") : "—"} />
                    </>
                  )}
                  {app.loanNote && (
                    <>
                      <Row label="Loan note token ID" value={app.loanNote.tokenId != null ? `#${app.loanNote.tokenId}` : "—"} bold />
                      <Row label="Chain status" value={app.loanNote.chainStatus ?? "—"} />
                      <Row label="Mint transaction" value={app.loanNote.txHash ?? "—"} />
                      <Row label="Audit hash (SHA-256)" value={app.loanNote.auditHash ?? "—"} />
                      <Row label="Audit transaction" value={app.loanNote.auditTxHash ?? "—"} />
                    </>
                  )}
                </dl>
              </Card>
            )}
          </>
        )}
      </main>
    </div>
  );
}
