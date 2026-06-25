import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowClockwise,
  ClockClockwise,
  WarningCircle,
  Code,
  SealCheck,
} from "@phosphor-icons/react";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const LEVEL_COLORS = {
  ERROR: { dot: "bg-loss", text: "text-loss", bg: "bg-loss/10", border: "border-loss/20" },
  WARNING: { dot: "bg-amber-500", text: "text-amber-500", bg: "bg-amber-500/10", border: "border-amber-500/20" },
  INFO: { dot: "bg-cuan", text: "text-cuan", bg: "bg-cuan/10", border: "border-cuan/20" },
  DEBUG: { dot: "bg-muted-foreground", text: "text-muted-foreground", bg: "bg-muted", border: "border-border" },
};

function getLevelColor(level) {
  return LEVEL_COLORS[level] || LEVEL_COLORS.DEBUG;
}

function AppLogs() {
  const token = localStorage.getItem("ihsg_admin_token");
  const [lines, setLines] = useState([]);
  const [totalLines, setTotalLines] = useState(0);
  const [loading, setLoading] = useState(false);
  const [levelFilter, setLevelFilter] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const pollRef = useRef(null);
  const scrollRef = useRef(null);

  const fetchLogs = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/admin/logs`, {
        params: { token, lines: 200, level: levelFilter || undefined },
      });
      if (resp.data?.success) {
        setLines(resp.data.lines);
        setTotalLines(resp.data.total_lines);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [token, levelFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(fetchLogs, 5000);
    return () => clearInterval(pollRef.current);
  }, [autoRefresh, fetchLogs]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <p className="text-xs text-muted-foreground">Total: {totalLines} baris</p>
          <div className="flex gap-1">
            {Object.keys(LEVEL_COLORS).map((lvl) => (
              <button
                key={lvl}
                className={`px-2 py-0.5 rounded text-[10px] font-medium border transition-colors ${
                  levelFilter === lvl
                    ? `${LEVEL_COLORS[lvl].bg} ${LEVEL_COLORS[lvl].border} ${LEVEL_COLORS[lvl].text}`
                    : "border-border text-muted-foreground hover:bg-muted"
                }`}
                onClick={() => setLevelFilter(levelFilter === lvl ? null : lvl)}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-[10px] text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh 5s
          </label>
          <Button
            className="h-7 text-[11px]"
            disabled={loading}
            onClick={fetchLogs}
            size="sm"
            variant="outline"
          >
            <ArrowClockwise className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      <Card className="border-border bg-foreground shadow-none">
        <CardContent className="p-0">
          <div
            ref={scrollRef}
            className="h-[500px] overflow-y-auto font-mono text-[11px] leading-5 p-3 text-background/80"
          >
            {lines.length === 0 ? (
              <p className="text-background/50 italic">Belum ada log...</p>
            ) : (
              lines.map((line, i) => {
                const levelMatch = line.match(/\b(ERROR|WARNING|INFO|DEBUG)\b/);
                const level = levelMatch ? levelMatch[1] : "INFO";
                const colors = getLevelColor(level);
                return (
                  <div
                    key={i}
                    className={`${colors.text} hover:bg-background/10 px-1 rounded`}
                  >
                    <span className="opacity-40 select-none mr-2">{i + 1}</span>
                    <span className="opacity-50">{line}</span>
                  </div>
                );
              })
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function LLMAudit() {
  const token = localStorage.getItem("ihsg_admin_token");
  const [calls, setCalls] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchAudit = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/admin/llm-audit`, {
        params: { token, limit: 100 },
      });
      if (resp.data?.success) {
        setCalls(resp.data.calls || []);
        setStats(resp.data.stats || null);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAudit();
  }, [fetchAudit]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        {stats && (
          <div className="flex gap-3 text-[11px] text-muted-foreground">
            <span>Total: {stats.total_calls} calls</span>
            <span>Success: {stats.success_rate}%</span>
            <span>Rata-rata: {stats.avg_execution_time}s</span>
          </div>
        )}
        <Button
          className="h-7 text-[11px]"
          disabled={loading}
          onClick={fetchAudit}
          size="sm"
          variant="outline"
        >
          <ArrowClockwise className={`mr-1 h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {stats && stats.by_agent && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(stats.by_agent).map(([agent, s]) => (
            <Badge
              key={agent}
              className={`text-[10px] ${
                s.success_rate >= 80
                  ? "bg-cuan/10 text-cuan"
                  : s.success_rate >= 50
                    ? "bg-amber-500/10 text-amber-600"
                    : "bg-loss/10 text-loss"
              }`}
            >
              {agent}: {s.total_calls} calls ({s.success_rate}%)
            </Badge>
          ))}
        </div>
      )}

      <Card className="border-border bg-card shadow-none">
        <CardContent className="p-0">
          <div className="max-h-[500px] overflow-y-auto">
            {calls.length === 0 ? (
              <p className="p-4 text-xs text-muted-foreground italic">Belum ada panggilan LLM...</p>
            ) : (
              <table className="w-full text-[11px]">
                <thead className="sticky top-0 bg-muted/50 text-[10px] uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="text-left px-3 py-2 font-medium">Waktu</th>
                    <th className="text-left px-3 py-2 font-medium">Agent</th>
                    <th className="text-left px-3 py-2 font-medium">Model</th>
                    <th className="text-right px-3 py-2 font-medium">Durasi</th>
                    <th className="text-right px-3 py-2 font-medium">Prompt</th>
                    <th className="text-right px-3 py-2 font-medium">Response</th>
                    <th className="text-center px-3 py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {calls.map((call, i) => (
                    <tr key={i} className="hover:bg-muted/30">
                      <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                        {new Date(call.timestamp).toLocaleTimeString("id-ID")}
                      </td>
                      <td className="px-3 py-2 font-medium text-foreground">
                        {call.agent_name}
                      </td>
                      <td className="px-3 py-2 text-muted-foreground max-w-[120px] truncate" title={call.model}>
                        {call.model}
                      </td>
                      <td className="px-3 py-2 text-right text-muted-foreground">
                        {call.execution_time.toFixed(1)}s
                      </td>
                      <td className="px-3 py-2 text-right text-muted-foreground">
                        {call.prompt_length.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-right text-muted-foreground">
                        {call.response_length.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {call.success ? (
                          <SealCheck className="h-3.5 w-3.5 text-cuan inline" weight="fill" />
                        ) : (
                          <span className="text-loss" title={call.error}>Gagal</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LogViewer() {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
          Real-time Monitoring
        </p>
        <h3 className="mt-1 text-sm font-semibold text-foreground">
          Log Backend &amp; LLM Audit
        </h3>
      </div>

      <Tabs defaultValue="app">
        <TabsList>
          <TabsTrigger value="app">
            <Code className="mr-1.5 h-3.5 w-3.5" />
            Application Logs
          </TabsTrigger>
          <TabsTrigger value="llm">
            <ClockClockwise className="mr-1.5 h-3.5 w-3.5" />
            LLM Audit Trail
          </TabsTrigger>
        </TabsList>

        <TabsContent className="mt-4" value="app">
          <AppLogs />
        </TabsContent>
        <TabsContent className="mt-4" value="llm">
          <LLMAudit />
        </TabsContent>
      </Tabs>
    </div>
  );
}
