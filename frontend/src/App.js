import { useCallback, useMemo, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Buildings, ChartLineUp, Coins, GlobeHemisphereWest } from "@phosphor-icons/react";
import "@/App.css";
import { Toaster } from "@/components/ui/sonner";
import AdminDashboard from "@/components/AdminDashboard";
import AppHeader from "@/components/AppHeader";
import CompanyDetailSheet from "@/components/CompanyDetailSheet";
import MacroDashboard from "@/components/MacroDashboard";
import NewsAnalysis from "@/components/AgentDashboard/NewsAnalysis";
import PredictionDashboard from "@/components/AgentDashboard/PredictionDashboard";
import ScreenerLayout from "@/components/ScreenerLayout";
import { SCREENER } from "@/constants/testIds";
import { adaptTVCompany, adaptTVCompanies } from "@/lib/tvAdapter";

function buildStatCards() {
  return [
    {
      label: "Sumber utama",
      value: "TV",
      description: "Custom TradingView screen",
      icon: Buildings,
    },
    {
      label: "Agent scoring",
      value: "AI",
      description: "Valuasi, kualitas, growth, risiko",
      icon: ChartLineUp,
    },
    {
      label: "Cache data",
      value: "1J",
      description: "Fallback saat sumber lambat",
      icon: Coins,
    },
  ];
}

function ScreenerPage() {
  const [tvData, setTvData] = useState([]);
  const [selectedTVCompany, setSelectedTVCompany] = useState(null);

  const formattedUpdatedAt = useMemo(() => {
    return new Intl.DateTimeFormat("id-ID", {
      dateStyle: "full",
      timeStyle: "short",
    }).format(new Date());
  }, []);

  const statCards = useMemo(() => buildStatCards(), []);

  const adaptedCompanies = useMemo(() => adaptTVCompanies(tvData), [tvData]);

  const handleTvDataUpdate = useCallback((data) => {
    setTvData(data || []);
  }, []);

  const handleSelectCompany = useCallback((item) => {
    setSelectedTVCompany(adaptTVCompany(item));
  }, []);

  const handleCloseSheet = useCallback((open) => {
    if (!open) setSelectedTVCompany(null);
  }, []);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.12),_transparent_28%),linear-gradient(180deg,_#f8fafc_0%,_#eff6ff_100%)]" data-testid={SCREENER.appShell}>
      <AppHeader />

      <ScreenerLayout
        formattedUpdatedAt={formattedUpdatedAt}
        onSelectCompany={handleSelectCompany}
        onTvDataUpdate={handleTvDataUpdate}
        statCards={statCards}
      />

      <CompanyDetailSheet
        company={selectedTVCompany}
        companies={adaptedCompanies}
        onOpenChange={handleCloseSheet}
        open={Boolean(selectedTVCompany)}
      />
    </div>
  );
}

function PredictionPage() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.12),_transparent_28%),linear-gradient(180deg,_#f8fafc_0%,_#eff6ff_100%)]">
      <AppHeader />
      <main className="mx-auto max-w-[1600px] space-y-10 px-4 py-6 sm:px-6 lg:px-8">
        <PredictionDashboard />
        <div className="border-t border-slate-200 pt-10">
          <NewsAnalysis />
        </div>
      </main>
    </div>
  );
}

function MacroPage() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.12),_transparent_28%),linear-gradient(180deg,_#f8fafc_0%,_#eff6ff_100%)]">
      <AppHeader />
      <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        <MacroDashboard />
      </main>
    </div>
  );
}

function AdminPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="mx-auto max-w-[1200px] px-4 py-6 sm:px-6 lg:px-8">
        <AdminDashboard />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<ScreenerPage />} path="/" />
        <Route element={<PredictionPage />} path="/prediction" />
        <Route element={<MacroPage />} path="/macro" />
        <Route element={<AdminPage />} path="/admin" />
      </Routes>
      <Toaster position="top-right" richColors />
    </BrowserRouter>
  );
}
