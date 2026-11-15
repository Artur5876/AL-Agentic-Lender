// AL-20 US-222: compare the seller's asking price with the ML valuation.
// Same rule as mobile (valuation/PriceComparison.kt) and the backend calculation module
// (ai/calc/metrics.py, price_vs_valuation, overvaluation_threshold in ai/calc/config.py):
//   difference = asking price - estimate
//   variance   = difference / estimate
//   over-valued when the asking price is MORE than 10% above the estimate (exactly 10% is not flagged).

// 10% as a fraction, like every ratio in the data model. Keep in step with mobile and ai/calc/config.py.
export const OVER_VALUATION_THRESHOLD = 0.1;

export interface PriceComparison {
  differenceEuro: number; // positive = asking price is above the estimate
  variance: number; // fraction of the estimate: 0.0395 = 3.95%
  isOverValued: boolean;
}

// Returns null when a number is missing or the estimate is 0 or less (cannot divide by it).
export function comparePrice(
  askingPrice: number | null | undefined,
  estimate: number | null | undefined,
): PriceComparison | null {
  if (askingPrice == null || estimate == null || estimate <= 0) return null;
  const differenceEuro = askingPrice - estimate;
  const variance = differenceEuro / estimate;
  return { differenceEuro, variance, isOverValued: variance > OVER_VALUATION_THRESHOLD };
}
