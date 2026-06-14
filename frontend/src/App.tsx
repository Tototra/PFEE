import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LayoutDashboard, MessageSquare, Zap } from 'lucide-react';
import { Link, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import { Chatbot } from './pages/Chatbot';
import { Dashboard } from './pages/Dashboard';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-slate-50">
      <nav className="flex w-56 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 p-4">
          <h1 className="text-lg font-bold text-slate-900">Coach IA GTB</h1>
          <p className="text-xs text-slate-500">PFEE EPITA × AER</p>
        </div>
        <ul className="flex-1 space-y-1 p-2">
          <li>
            <Link
              to="/"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
            >
              <LayoutDashboard className="h-4 w-4" /> Dashboard
            </Link>
          </li>
          <li>
            <Link
              to="/chat"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
            >
              <MessageSquare className="h-4 w-4" /> Chatbot
            </Link>
          </li>
          <li>
            <Link
              to="/energy"
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
            >
              <Zap className="h-4 w-4" /> Énergie
            </Link>
          </li>
        </ul>
        <div className="border-t border-slate-200 p-3 text-xs text-slate-400">
          v0.1.0 · Sprint S1-S2
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<Chatbot />} />
            <Route
              path="/energy"
              element={
                <div className="p-6">
                  <h1 className="text-2xl font-bold text-slate-900">Énergie</h1>
                  <p className="mt-2 text-sm text-slate-500">
                    Module à développer en Sprint S25-S27.
                  </p>
                </div>
              }
            />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}
