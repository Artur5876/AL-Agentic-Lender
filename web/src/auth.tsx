import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { onAuthStateChanged, signInWithEmailAndPassword, signOut, type User } from "firebase/auth";
import { auth } from "./firebase";
import type { Role } from "./types";

interface AuthState {
  loading: boolean;
  user: User | null;
  /** "broker" | "underwriter", or null for borrowers / users without the claim (AL-14). */
  role: Role | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<Role | null>(null);

  useEffect(() => {
    return onAuthStateChanged(auth, async (u) => {
      if (!u) {
        setUser(null);
        setRole(null);
        setLoading(false);
        return;
      }
      // The role is a custom claim set by the backend/seed script. No claim = borrower.
      const token = await u.getIdTokenResult();
      const claim = token.claims.role;
      setRole(claim === "broker" || claim === "underwriter" ? claim : null);
      setUser(u);
      setLoading(false);
    });
  }, []);

  const login = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password);
  };
  const logout = async () => {
    try {
      await signOut(auth);
    } catch (e) {
      console.error("signOut failed", e);
    }
    setUser(null);
    setRole(null);
    // Full page load of the login page: clears everything, no routing involved.
    window.location.assign("/login");
  };

  return (
    <AuthContext.Provider value={{ loading, user, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
