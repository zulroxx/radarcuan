import { useCallback, useEffect, useState } from "react";
import {
  ArrowClockwise,
  LockKey,
  SignOut,
  Article,
  Users,
  Eye,
  EyeClosed,
  Circle,
  CheckCircle,
  WarningCircle,
  Clock,
  PlayCircle,
  MagicWand,
  Scroll,
  Trash,
  AlertCircle,
} from "@phosphor-icons/react";
import PlaygroundPanel from "@/components/PlaygroundPanel";
import LogViewer from "@/components/LogViewer";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;
const ADMIN_TOKEN_KEY = "ihsg_admin_token";

function LoginForm({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      toast.error("Username dan password wajib diisi.");
      return;
    }
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/admin/login`, { username, password });
      if (response.data?.success) {
        localStorage.setItem(ADMIN_TOKEN_KEY, response.data.token);
        onLogin();
        toast.success("Login berhasil.");
      }
    } catch (err) {
      const msg = err.response?.data?.detail || "Login gagal.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [username, password, onLogin]);

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-sm flex-col justify-center">
      <Card className="border-border bg-card shadow-sm">
        <CardHeader className="items-center space-y-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-foreground">
            <LockKey className="h-6 w-6 text-background" weight="fill" />
          </div>
          <CardTitle className="text-lg text-foreground">Admin Panel</CardTitle>
          <p className="text-sm text-muted-foreground">Masuk untuk melihat log feedback & waitlist.</p>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-xs font-medium text-foreground" htmlFor="username">Username</label>
              <Input
                autoComplete="username"
                id="username"
                name="username"
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                value={username}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-foreground" htmlFor="password">Password</label>
              <div className="relative">
                <Input
                  autoComplete="current-password"
                  id="password"
                  name="password"
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSubmit(e)}
                  placeholder="••••••"
                  type={showPassword ? "text" : "password"}
                  value={password}
                />
                <button
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  type="button"
                >
                  {showPassword ? <EyeClosed className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <Button className="w-full" disabled={loading} type="submit">
              {loading ? "Memverifikasi..." : "Masuk"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function FeedbackTable({ data }) {
  if (!data?.length) {
    return (
      <div className="flex flex-col items-center py-12 text-sm text-muted-foreground">
        Belum ada data feedback.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[600px]">
        <thead>
          <tr className="bg-muted/50">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Waktu</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Nama</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Email</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Pesan</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-muted/30">
              <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                {new Date(item.created_at).toLocaleString("id-ID")}
              </td>
              <td className="px-4 py-3 text-sm text-foreground">{item.name || "-"}</td>
              <td className="px-4 py-3 text-sm text-foreground">{item.email || "-"}</td>
              <td className="max-w-xs truncate px-4 py-3 text-sm text-muted-foreground">{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WaitlistTable({ data }) {
  if (!data?.length) {
    return (
      <div className="flex flex-col items-center py-12 text-sm text-muted-foreground">
        Belum ada data waitlist.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[600px]">
        <thead>
          <tr className="bg-muted/50">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Waktu</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Email</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Catatan</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-muted/30">
              <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                {new Date(item.created_at).toLocaleString("id-ID")}
              </td>
              <td className="px-4 py-3 text-sm text-foreground">{item.email}</td>
              <td className="max-w-xs truncate px-4 py-3 text-sm text-muted-foreground">{item.note || "-"}</td>
              <td className="px-4 py-3">
                <Badge className="bg-cuan/10 text-cuan">
                  {item.status || "active"}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const AGENT_LABELS = {
  scheduler: "Scheduler (Periodik)",
  tradingview: "TradingView Screener",
  macro: "Makro Ekonomi",
  news_flow: "Analisis Berita",
  sector_predictions: "Prediksi Sektor",
  stock_recommendations: "Rekomendasi Saham",
  order_book: "Order Book Simulation",
};

const STATUS_CONFIG = {
  ok: { icon: CheckCircle, class: "text-cuan", label: "OK" },
  error: { icon: WarningCircle, class: "text-loss", label: "Error" },
  running: { icon: Clock, class: "text-amber-500", label: "Berjalan" },
  unknown: { icon: Circle, class: "text-muted-foreground", label: "Tidak Diketahui" },
};

function AgentStatusCard({ agentKey, status, onTrigger, triggering }) {
  const cfg = STATUS_CONFIG[status?.status] || STATUS_CONFIG.unknown;
  const Icon = cfg.icon;
  const lastError = status?.last_error || "";
  const lastRun = status?.last_run || "";
  const cacheAge = status?.cache_age_seconds;
  const cacheAgeText = cacheAge != null
    ? cacheAge < 60 ? `${Math.round(cacheAge)} detik`
      : cacheAge < 3600 ? `${Math.round(cacheAge / 60)} menit`
        : `${(cacheAge / 3600).toFixed(1)} jam`
    : "-";

  const canTrigger = agentKey !== "scheduler" && onTrigger;

  return (
    <Card className={`border bg-card shadow-none ${
      status?.status === "error"
        ? "border-loss/20"
        : status?.status === "unknown"
          ? "border-amber-500/20"
          : "border-border"
    }`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-foreground">
              {AGENT_LABELS[agentKey] || agentKey}
            </p>
            {lastRun && (
              <p className="mt-0.5 text-[10px] text-muted-foreground">
                {new Date(lastRun).toLocaleString("id-ID")}
              </p>
            )}
            {lastError && (
              <p className="mt-1 truncate text-[10px] text-loss" title={lastError}>
                {lastError}
              </p>
            )}
            <p className="mt-0.5 text-[10px] text-muted-foreground">Cache: {cacheAgeText}</p>
          </div>
          <div className="flex flex-col items-center justify-between gap-2 min-h-[60px]">
            <Icon className={`h-5 w-5 shrink-0 ${cfg.class}`} weight="fill" />
            <button
              className={`h-6 rounded px-2 text-[10px] font-medium transition-colors ${
                canTrigger
                  ? triggering
                    ? "cursor-not-allowed bg-muted text-muted-foreground"
                    : "bg-muted/50 text-muted-foreground hover:bg-muted"
                  : "invisible"
              }`}
              disabled={!canTrigger || triggering}
              onClick={canTrigger ? () => onTrigger(agentKey) : undefined}
              title={`Jalankan ${AGENT_LABELS[agentKey] || agentKey}`}
              type="button"
            >
              {triggering ? "..." : "Jalankan"}
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AgentStatusPanel() {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  const [statuses, setStatuses] = useState({});
  const [loading, setLoading] = useState(false);
  const [triggerAll, setTriggerAll] = useState(false);
  const [triggeringAgents, setTriggeringAgents] = useState({});

  const fetchStatus = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/admin/agent-status`, { params: { token } });
      if (resp.data?.success) {
        setStatuses(resp.data.data || {});
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [token]);

  const triggerAgent = useCallback(async (agent) => {
    if (!token) return;
    setTriggeringAgents((prev) => ({ ...prev, [agent]: true }));
    try {
      const resp = await axios.post(`${API_BASE}/admin/trigger-agent?agent=${agent}&token=${token}`);
      if (resp.data?.success) {
        toast.success(`${AGENT_LABELS[agent] || agent} berhasil dijalankan.`);
      } else {
        toast.info(resp.data?.message || "Agent sedang berjalan.");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || `Gagal menjalankan ${AGENT_LABELS[agent] || agent}`);
    } finally {
      setTriggeringAgents((prev) => ({ ...prev, [agent]: false }));
      fetchStatus();
    }
  }, [token, fetchStatus]);

  const triggerAllAgents = useCallback(async () => {
    if (!token || triggerAll) return;
    setTriggerAll(true);
    try {
      const resp = await axios.post(`${API_BASE}/admin/refresh-cache?token=${token}`);
      if (resp.data?.success) {
        toast.success("Semua AI Agent berjalan.");
      } else {
        toast.info(resp.data?.message || "Agent sedang berjalan.");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Gagal trigger agent");
    } finally {
      setTriggerAll(false);
    }
  }, [token, triggerAll]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const agentKeys = Object.keys(AGENT_LABELS);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <p className="text-sm text-muted-foreground">
          Status seluruh agen sistem. <span className="text-cuan">Hijau</span> = OK,{" "}
          <span className="text-loss">Merah</span> = Error,{" "}
          <span className="text-amber-500">Kuning</span> = Sedang berjalan.
        </p>
        <div className="flex items-center gap-2">
          <Button
            className="h-7 text-[11px]"
            disabled={triggerAll}
            onClick={triggerAllAgents}
            size="sm"
            variant="default"
          >
            <PlayCircle className={`mr-1 h-3 w-3 ${triggerAll ? "animate-pulse" : ""}`} />
            {triggerAll ? "Menjalankan..." : "Jalankan Semua"}
          </Button>
          <Button
            className="h-7 text-[11px]"
            disabled={loading}
            onClick={fetchStatus}
            size="sm"
            variant="outline"
          >
            <ArrowClockwise className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {agentKeys.map((key) => (
          <AgentStatusCard
            key={key}
            agentKey={key}
            status={statuses[key]}
            onTrigger={triggerAgent}
            triggering={triggeringAgents[key]}
          />
        ))}
      </div>
    </div>
  );
}

function CacheManagement() {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY);
  const [selectedCaches, setSelectedCaches] = useState([]);
  const [deleting, setDeleting] = useState(false);

  const CACHE_OPTIONS = [
    { key: "news_flow", label: "News Flow (Analisis Berita)" },
    { key: "tradingview", label: "TradingView Screener" },
    { key: "macro", label: "Macro Ekonomi" },
    { key: "sector_predictions", label: "Prediksi Sektor" },
    { key: "stock_recommendations", label: "Rekomendasi Saham" },
  ];

  const handleCacheToggle = (cacheKey) => {
    setSelectedCaches((prev) => {
      if (prev.includes(cacheKey)) {
        return prev.filter((c) => c !== cacheKey);
      }
      return [...prev, cacheKey];
    });
  };

  const handleSelectAll = () => {
    setSelectedCaches((prev) => {
      if (prev.length === CACHE_OPTIONS.length) {
        return [];
      }
      return CACHE_OPTIONS.map((c) => c.key);
    });
  };

  const handleDeleteCache = async () => {
    if (!selectedCaches.length) {
      toast.warning("Pilih cache yang ingin dihapus");
      return;
    }

    setDeleting(true);
    try {
      const response = await axios.post(
        `${API_BASE}/admin/cache/delete?token=${token}`,
        { caches: selectedCaches }
      );
      if (response.data?.success) {
        toast.success(
          `Cache dihapus: ${response.data.deleted_mongo?.length || 0} MongoDB, ${response.data.deleted_file?.length || 0} file`
        );
        setSelectedCaches([]);
      } else {
        toast.error(response.data?.message || "Gagal menghapus cache");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Gagal menghapus cache");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Card className="border-border bg-card shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Trash className="h-4 w-4" />
          Manajemen Cache
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          Pilih cache yang ingin dihapus. Order Book cache tidak dapat dihapus.
        </p>
        
        <div className="space-y-2">
          <div className="flex items-center gap-2 pb-2 border-b border-border">
            <Checkbox
              checked={selectedCaches.length === CACHE_OPTIONS.length}
              onCheckedChange={handleSelectAll}
              id="select-all"
            />
            <label
              htmlFor="select-all"
              className="text-xs font-medium text-foreground cursor-pointer"
            >
              Pilih Semua
            </label>
          </div>

          {CACHE_OPTIONS.map((option) => (
            <div key={option.key} className="flex items-center gap-2">
              <Checkbox
                checked={selectedCaches.includes(option.key)}
                onCheckedChange={() => handleCacheToggle(option.key)}
                id={option.key}
              />
              <label
                htmlFor={option.key}
                className="text-xs text-foreground cursor-pointer"
              >
                {option.label}
              </label>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-2 pt-2">
          <Button
            size="sm"
            variant="destructive"
            disabled={deleting || !selectedCaches.length}
            onClick={handleDeleteCache}
            className="h-7 text-[11px]"
          >
            <Trash className="mr-1 h-3 w-3" />
            {deleting ? "Menghapus..." : "Hapus Cache"}
          </Button>
          {selectedCaches.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {selectedCaches.length} dipilih
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function AdminDashboard() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!localStorage.getItem(ADMIN_TOKEN_KEY));
  const [feedbackData, setFeedbackData] = useState([]);
  const [waitlistData, setWaitlistData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("feedback");
  const [aiHealth, setAiHealth] = useState({ healthy: true, total: 0, ok: 0, errors: 0, unknowns: 0 });

  const checkAiHealth = useCallback(async () => {
    const token = localStorage.getItem(ADMIN_TOKEN_KEY);
    if (!token) return;
    try {
      const resp = await axios.get(`${API_BASE}/admin/agent-status`, { params: { token } });
      if (resp.data?.success) {
        const agents = Object.values(resp.data.data);
        setAiHealth({
          healthy: agents.every(a => a.status !== "error"),
          total: agents.length,
          ok: agents.filter(a => a.status === "ok").length,
          errors: agents.filter(a => a.status === "error").length,
          unknowns: agents.filter(a => a.status === "unknown").length,
        });
      }
    } catch {} // silent
  }, []);

  const fetchData = useCallback(async (tab) => {
    const token = localStorage.getItem(ADMIN_TOKEN_KEY);
    if (!token) return;

    setLoading(true);
    try {
      const endpoint = tab === "feedback" ? "feedback" : "waitlist";
      const response = await axios.get(`${API_BASE}/admin/${endpoint}`, {
        params: { token },
      });
      if (response.data?.success) {
        if (tab === "feedback") setFeedbackData(response.data.data);
        else setWaitlistData(response.data.data);
      }
    } catch (err) {
      if (err.response?.status === 401) {
        localStorage.removeItem(ADMIN_TOKEN_KEY);
        setIsLoggedIn(false);
        toast.error("Sesi habis. Silakan login ulang.");
      } else {
        toast.error(err.response?.data?.detail || "Gagal mengambil data");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTabChange = useCallback((tab) => {
    setActiveTab(tab);
    if (tab !== "agents" && tab !== "playground" && tab !== "logs") fetchData(tab);
  }, [fetchData]);

  // Initial fetch on login
  useEffect(() => {
    if (isLoggedIn) {
      fetchData("feedback");
      fetchData("waitlist");
      checkAiHealth();
    }
  }, [isLoggedIn]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLogout = useCallback(() => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    setIsLoggedIn(false);
    setFeedbackData([]);
    setWaitlistData([]);
  }, []);

  if (!isLoggedIn) {
    return <LoginForm onLogin={() => setIsLoggedIn(true)} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            Admin Panel
          </p>
          <h2 className="mt-1 text-lg font-semibold text-foreground sm:text-xl">
            Log Feedback & Waitlist
          </h2>
        </div>
        <Button onClick={handleLogout} size="sm" variant="outline">
          <SignOut className="mr-1.5 h-4 w-4" />
          Keluar
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Card className="border-border bg-card shadow-none">
          <CardContent className="p-3 sm:p-4">
            <div className="flex items-center gap-2">
              <Article className="h-4 w-4 text-chart-1" weight="fill" />
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Feedback</p>
            </div>
            <p className="mt-2 text-2xl font-semibold text-foreground">{feedbackData.length}</p>
          </CardContent>
        </Card>
        <Card className="border-border bg-card shadow-none">
          <CardContent className="p-3 sm:p-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-cuan" weight="fill" />
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Waitlist</p>
            </div>
            <p className="mt-2 text-2xl font-semibold text-foreground">{waitlistData.length}</p>
          </CardContent>
        </Card>
        <Card className={`border bg-card shadow-none ${
          aiHealth.errors > 0
            ? "border-loss/20"
            : aiHealth.unknowns > 0
              ? "border-amber-500/20"
              : "border-border"
        }`}>
          <CardContent className="p-3 sm:p-4">
            <div className="flex items-center gap-2">
              {aiHealth.errors > 0 ? (
                <WarningCircle className="h-4 w-4 text-loss" weight="fill" />
              ) : (
                <CheckCircle className="h-4 w-4 text-cuan" weight="fill" />
              )}
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">AI Status</p>
            </div>
            <p className={`mt-2 text-2xl font-semibold ${
              aiHealth.errors > 0 ? "text-loss" : "text-cuan"
            }`}>
              {aiHealth.errors > 0 ? "Bad" : "Healthy"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {aiHealth.ok}/{aiHealth.total} agen OK
              {aiHealth.errors > 0 && `, ${aiHealth.errors} error`}
              {aiHealth.unknowns > 0 && `, ${aiHealth.unknowns} unknown`}
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs onValueChange={handleTabChange} value={activeTab}>
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <TabsList className="flex flex-wrap sm:inline-flex sm:flex-nowrap h-auto sm:h-9">
            <TabsTrigger value="feedback" className="flex-1 sm:flex-auto min-w-[100px] sm:min-w-fit">
              <Article className="mr-1.5 h-3.5 w-3.5" />
              Feedback
            </TabsTrigger>
            <TabsTrigger value="waitlist" className="flex-1 sm:flex-auto min-w-[100px] sm:min-w-fit">
              <Users className="mr-1.5 h-3.5 w-3.5" />
              Waitlist
            </TabsTrigger>
            <TabsTrigger value="agents" className="flex-1 sm:flex-auto min-w-[100px] sm:min-w-fit">
              <Circle className="mr-1.5 h-3.5 w-3.5" />
              Agent Status
            </TabsTrigger>
            <TabsTrigger value="playground" className="flex-1 sm:flex-auto min-w-[100px] sm:min-w-fit">
              <MagicWand className="mr-1.5 h-3.5 w-3.5" />
              Playground
            </TabsTrigger>
            <TabsTrigger value="logs" className="flex-1 sm:flex-auto min-w-[100px] sm:min-w-fit">
              <Scroll className="mr-1.5 h-3.5 w-3.5" />
              Logs
            </TabsTrigger>
          </TabsList>
          {activeTab !== "agents" && activeTab !== "logs" && (
            <Button
              className="h-7 text-[11px] shrink-0 sm:ml-auto"
              disabled={loading}
              onClick={() => fetchData(activeTab)}
              size="sm"
              variant="outline"
            >
              <ArrowClockwise className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          )}
        </div>

        <TabsContent className="mt-4" value="feedback">
          <FeedbackTable data={feedbackData} />
        </TabsContent>
        <TabsContent className="mt-4" value="waitlist">
          <WaitlistTable data={waitlistData} />
        </TabsContent>
        <TabsContent className="mt-4" value="agents">
          <div className="space-y-4">
            <AgentStatusPanel />
            <CacheManagement />
          </div>
        </TabsContent>
        <TabsContent className="mt-4" value="playground">
          <PlaygroundPanel />
        </TabsContent>
        <TabsContent className="mt-4" value="logs">
          <LogViewer />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default AdminDashboard;
