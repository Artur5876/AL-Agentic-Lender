import { useAuth } from "../auth";

export default function NoAccess() {
  const { logout } = useAuth();
  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="max-w-sm bg-white rounded-xl shadow p-6 space-y-4 text-center">
        <h1 className="text-xl font-semibold text-slate-900">No portal access</h1>
        <p className="text-sm text-slate-600">
          This portal is for brokers and underwriting officers. Borrowers should use the AL mobile app.
        </p>
        <button onClick={logout} className="rounded bg-slate-800 px-4 py-2 text-white text-sm">
          Sign out
        </button>
      </div>
    </main>
  );
}
