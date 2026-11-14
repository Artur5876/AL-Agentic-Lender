import { useEffect, useRef, useState } from "react";

// Matches the API limit on StatusChange.reason (backend/app/models.py: max_length=1000).
const MAX_REASON = 1000;

interface Props {
  title: string; // e.g. "Decline application"
  subtitle?: string; // e.g. the applicant and reference
  confirmLabel: string; // e.g. "Decline"
  confirmClass: string; // Tailwind colour classes for the confirm button
  // Resolve to close the dialog; throw an Error to keep it open and show its message.
  onConfirm: (reason: string) => Promise<void>;
  onCancel: () => void;
}

/**
 * AL-25 / US-252: a written reason is mandatory for Decline and Conditionally approve.
 * The Confirm button stays off until there is a non-blank reason; the API checks it again
 * (422 reason_required), and its message is shown here if it is rejected.
 */
export default function ReasonDialog({ title, subtitle, confirmLabel, confirmClass, onConfirm, onCancel }: Props) {
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const box = useRef<HTMLTextAreaElement>(null);

  useEffect(() => box.current?.focus(), []);

  const trimmed = reason.trim();

  async function submit() {
    if (!trimmed || saving) return;
    setSaving(true);
    setError(null);
    try {
      await onConfirm(trimmed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the decision.");
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reason-title"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl">
        <h2 id="reason-title" className="text-lg font-semibold text-slate-900">
          {title}
        </h2>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}

        <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="reason-box">
          Reason (required)
        </label>
        <textarea
          id="reason-box"
          ref={box}
          value={reason}
          maxLength={MAX_REASON}
          onChange={(e) => setReason(e.target.value)}
          rows={4}
          className="mt-1 w-full rounded border border-slate-300 p-2 text-sm"
          placeholder="Explain the decision. It is stored with the decision and kept for audit."
        />
        <div className="mt-1 flex justify-between text-xs text-slate-400">
          <span>{trimmed ? "" : "A written reason is needed to continue."}</span>
          <span>
            {reason.length}/{MAX_REASON}
          </span>
        </div>

        {error && <p className="mt-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}

        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={saving}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={!trimmed || saving}
            className={`rounded px-3 py-1.5 text-sm text-white disabled:opacity-50 ${confirmClass}`}
          >
            {saving ? "Saving…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
