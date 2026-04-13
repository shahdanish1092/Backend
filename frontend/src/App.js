import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { useEffect } from 'react';
import { Toaster } from "sonner";
import { Sidebar, TopBar } from "./components";
import { useAuth } from "./hooks";
import {
  LandingPage,
  DashboardPage,
  InvoiceManagerPage,
  ApprovalCenterPage,
  MeetingSummarizerPage,
  HRConnectPage,
  SettingsPage,
} from "./pages";
import "./App.css";

// Protected route wrapper
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
}

// Dashboard layout with sidebar
function DashboardLayout() {
  const { user, logout } = useAuth();

  const handleDisconnect = () => {
    logout();
    window.location.href = '/';
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <div className="lg:pl-64">
        <TopBar userEmail={user?.email} onDisconnect={handleDisconnect} />
        <main className="p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

function App() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const userEmail = params.get('user_email');
    const auth = params.get('auth');
    if (auth === 'success' && userEmail) {
      localStorage.setItem('user_email', userEmail);
      window.history.replaceState({}, '', '/dashboard');
      window.location.reload();
    }
  }, []);
  return (
    <div className="App font-jakarta">
      <Toaster 
        position="top-right" 
        toastOptions={{
          style: {
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          },
        }}
      />
      <BrowserRouter>
        <Routes>
          {/* Public route */}
          <Route path="/" element={<LandingPage />} />

          {/* Protected routes with dashboard layout */}
          <Route
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/invoices" element={<InvoiceManagerPage />} />
            <Route path="/approvals" element={<ApprovalCenterPage />} />
            <Route path="/meetings" element={<MeetingSummarizerPage />} />
            <Route path="/hr-connect" element={<HRConnectPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
