// Shapes follow docs/data-model.md (draft v0.1). If the team changes the model, change it here.

export type Role = "broker" | "underwriter";

export const STATUS_LABELS = {
  applied: "Applied",
  ai_deliberated: "AI Deliberated",
  conditionally_approved: "Conditionally Approved",
  underwriter_approved: "Underwriter Approved",
  funded: "Funded",
  declined: "Declined",
  closed: "Closed",
} as const;

export type Status = keyof typeof STATUS_LABELS;
export const STATUSES = Object.keys(STATUS_LABELS) as Status[];

export type RiskTier = "low" | "medium" | "high";
export const RISK_TIERS: RiskTier[] = ["low", "medium", "high"];

export interface Application {
  id: string; // document ID, e.g. "AL-2026-0117"
  reference?: string;
  borrowerId: string;
  borrowerName: string;
  brokerId: string | null;
  status: Status;
  buyerType?: "first_time" | "subsequent";
  property?: {
    county?: string;
    propertyType?: string;
    askingPrice?: number;
    floorAreaM2?: number;
    bedrooms?: number;
    ber?: string;
  };
  financials?: {
    grossAnnualIncome?: number;
    monthlyDebts?: number;
    deposit?: number;
    loanAmount?: number;
    termYears?: number;
  };
  valuation?: {
    estimate?: number;
    low?: number;
    high?: number;
    modelVersion?: string;
  } | null;
  // Ratios are FRACTIONS (0.882 = 88.2%); lti is a multiple (3.5 = 3.5x income).
  // metrics is null until US-410 is connected; lti/dti/stressedDti are null when income is 0.
  metrics?: {
    lti?: number | null;
    ltv?: number | null;
    dti?: number | null;
    stressedDti?: number | null;
    monthlyRepayment?: number | null;
    checks?: { ltiOk?: boolean; ltvOk?: boolean; dtiOk?: boolean; stressedDtiOk?: boolean };
  } | null;
  // Null until someone decides who sets it (open decision 1 in the data model).
  riskTier?: RiskTier | null;
}

export type LtvBand = "le80" | "80to90" | "gt90" | "unknown";

export const LTV_BAND_LABELS: Record<LtvBand, string> = {
  le80: "≤ 80%",
  "80to90": "80–90%",
  gt90: "> 90%",
  unknown: "Unknown",
};

export function ltvBand(ltv: number | null | undefined): LtvBand {
  if (ltv === null || ltv === undefined) return "unknown";
  if (ltv <= 0.8) return "le80";
  if (ltv <= 0.9) return "80to90";
  return "gt90";
}
