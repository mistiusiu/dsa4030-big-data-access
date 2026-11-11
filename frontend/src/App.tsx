import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import { Layout } from "@/components/Layout";
import { Spinner } from "@/components/ui";
import { useTokens } from "@/lib/tokens";
import Login from "@/pages/Login";
import Overview from "@/pages/Overview";
import Lake from "@/pages/Lake";
import DatasetExplorer from "@/pages/DatasetExplorer";
import Workbench from "@/pages/Workbench";
import Grid from "@/pages/Grid";
import TokenLab from "@/pages/TokenLab";
import Audit from "@/pages/Audit";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { access } = useTokens();
  const { loading, me } = useAuth();
  const location = useLocation();
  if (!access) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (loading || !me) return <div className="p-10"><Spinner label="Verifying your token…" /></div>;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<Overview />} />
          <Route path="lake" element={<Lake />} />
          <Route path="lake/:slug" element={<DatasetExplorer />} />
          <Route path="workbench" element={<Workbench />} />
          <Route path="grid" element={<Grid />} />
          <Route path="tokens" element={<TokenLab />} />
          <Route path="audit" element={<Audit />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
