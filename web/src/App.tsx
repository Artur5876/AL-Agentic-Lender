import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import NoAccess from "./pages/NoAccess";
import Queue from "./pages/Queue";

export default function App() {
  return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/no-access" element={<NoAccess />} />
        <Route
            path="/"
            element={
              <ProtectedRoute>
                <Queue />
              </ProtectedRoute>
            }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
  );
}