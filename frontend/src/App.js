import { useCallback, useMemo, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Buildings, ChartLineUp, Coins } from "@phosphor-icons/react";
import { Toaster } from "@/components/ui/sonner";
import { SpeedInsights } from "@vercel/speed-insights/react";
import AdminDashboard from "@/components/AdminDashboard";
import AppHeader from "@/components/AppHeader";
import CompanyDetailSheet from "@/components/CompanyDetailSheet";
import MacroDashboard from "@/components/MacroDashboard";
import About from "@/components/About";
import OrderBook from "@/components/OrderBook";
import NewsAnalysis from "@/components/AgentDashboard/NewsAnalysis";
import PredictionDashboard from "@/components/AgentDashboard/PredictionDashboard";
import ScreenerLayout from "@/components/ScreenerLayout";
import { SCREENER } from "@/constants/testIds";
import { adaptTVCompany, adaptTVCompanies } from "@/lib/tvAdapter";

function PageShell({ children, className = "" }) {
  return (
    <div className={`min-h-screen bg-background ${className}`}>
      <AppHeader />
      <main className="mx-auto max-w-[1600px] px-4 py-5 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}

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
    <div className="min-h-screen bg-background" data-testid={SCREENER.appShell}>
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
    <PageShell>
      <div className="space-y-6">
        <PredictionDashboard />
        <div className="border-t border-border pt-6">
          <NewsAnalysis />
        </div>
      </div>
    </PageShell>
  );
}

function OrderBookPage() {
  return (
    <PageShell>
      <OrderBook />
    </PageShell>
  );
}

function AboutPage() {
  return (
    <PageShell>
      <div className="mx-auto max-w-[900px]">
        <About />
      </div>
    </PageShell>
  );
}

function MacroPage() {
  return (
    <PageShell>
      <MacroDashboard />
    </PageShell>
  );
}

function AdminPage() {
  return (
    <PageShell>
      <div className="mx-auto max-w-[1200px]">
        <AdminDashboard />
      </div>
    </PageShell>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<ScreenerPage />} path="/" />
        <Route element={<PredictionPage />} path="/prediction" />
        <Route element={<OrderBookPage />} path="/order-book" />
        <Route element={<AboutPage />} path="/about" />
        <Route element={<MacroPage />} path="/macro" />
        <Route element={<AdminPage />} path="/admin" />
      </Routes>
      <Toaster position="top-right" richColors />
      <SpeedInsights />
    </BrowserRouter>
  );
}
