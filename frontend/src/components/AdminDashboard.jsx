import { useCallback, useEffect, useState } from "react";
import {
  ArrowClockwise,
  LockKey,
  SignOut,
  Article,
  Users,
  Eye,
  EyeClosed,
} from "@phosphor-icons/react";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
      <Card className="border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <CardHeader className="items-center space-y-3 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-950">
            <LockKey className="h-6 w-6 text-white" weight="fill" />
          </div>
          <CardTitle className="text-lg text-slate-950 dark:text-slate-50">Admin Panel</CardTitle>
          <p className="text-sm text-slate-500 dark:text-slate-400">Masuk untuk melihat log feedback & waitlist.</p>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-700 dark:text-slate-200" htmlFor="username">Username</label>
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
              <label className="text-xs font-medium text-slate-700 dark:text-slate-200" htmlFor="password">Password</label>
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
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
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
      <div className="flex flex-col items-center py-12 text-sm text-slate-500 dark:text-slate-400">
        Belum ada data feedback.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full min-w-[600px]">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-800">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Waktu</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Nama</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Email</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Pesan</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800">
              <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                {new Date(item.created_at).toLocaleString("id-ID")}
              </td>
              <td className="px-4 py-3 text-sm text-slate-800 dark:text-slate-100">{item.name || "-"}</td>
              <td className="px-4 py-3 text-sm text-slate-800 dark:text-slate-100">{item.email || "-"}</td>
              <td className="max-w-xs truncate px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{item.message}</td>
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
      <div className="flex flex-col items-center py-12 text-sm text-slate-500 dark:text-slate-400">
        Belum ada data waitlist.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full min-w-[600px]">
        <thead>
          <tr className="bg-slate-50 dark:bg-slate-800">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Waktu</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Email</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Catatan</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800">
              <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                {new Date(item.created_at).toLocaleString("id-ID")}
              </td>
              <td className="px-4 py-3 text-sm text-slate-800 dark:text-slate-100">{item.email}</td>
              <td className="max-w-xs truncate px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{item.note || "-"}</td>
              <td className="px-4 py-3">
                <Badge className="bg-emerald-100 text-emerald-700 hover:!bg-emerald-100 focus:!ring-0">
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

function AdminDashboard() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!localStorage.getItem(ADMIN_TOKEN_KEY));
  const [feedbackData, setFeedbackData] = useState([]);
  const [waitlistData, setWaitlistData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("feedback");

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

  useEffect(() => {
    if (isLoggedIn) {
      fetchData(activeTab);
    }
  }, [isLoggedIn, activeTab, fetchData]);

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
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
            Admin Panel
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950 sm:text-xl dark:text-slate-50">
            Log Feedback & Waitlist
          </h2>
        </div>
        <Button onClick={handleLogout} size="sm" variant="outline">
          <SignOut className="mr-1.5 h-4 w-4" />
          Keluar
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-2">
        <Card className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-900">
          <CardContent className="p-3 sm:p-4">
            <div className="flex items-center gap-2">
              <Article className="h-4 w-4 text-sky-600" weight="fill" />
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Feedback</p>
            </div>
            <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-slate-50">{feedbackData.length}</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-900">
          <CardContent className="p-3 sm:p-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-emerald-600" weight="fill" />
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Waitlist</p>
            </div>
            <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-slate-50">{waitlistData.length}</p>
          </CardContent>
        </Card>
      </div>

      <Tabs onValueChange={setActiveTab} value={activeTab}>
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="feedback">
              <Article className="mr-1.5 h-3.5 w-3.5" />
              Feedback
            </TabsTrigger>
            <TabsTrigger value="waitlist">
              <Users className="mr-1.5 h-3.5 w-3.5" />
              Waitlist
            </TabsTrigger>
          </TabsList>
          <Button
            className="h-7 text-[11px]"
            disabled={loading}
            onClick={() => fetchData(activeTab)}
            size="sm"
            variant="outline"
          >
            <ArrowClockwise className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        <TabsContent className="mt-4" value="feedback">
          <FeedbackTable data={feedbackData} />
        </TabsContent>
        <TabsContent className="mt-4" value="waitlist">
          <WaitlistTable data={waitlistData} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default AdminDashboard;
