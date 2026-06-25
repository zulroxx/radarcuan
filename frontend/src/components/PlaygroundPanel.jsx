import { useCallback, useState } from "react";
import {
  PaperPlaneRight,
  CaretDown,
  CaretRight,
  FloppyDisk,
  Code,
  MagnifyingGlass,
  Image,
  Sparkle,
  Robot,
  ChatText,
} from "@phosphor-icons/react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (
  process.env.REACT_APP_BACKEND_URL || "http://localhost:8000"
).replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const CAPABILITIES = [
  { value: "none", label: "None", icon: Sparkle },
  { value: "premium_search", label: "Premium Search", icon: MagnifyingGlass },
  { value: "search", label: "Search", icon: MagnifyingGlass },
  { value: "code", label: "Code", icon: Code },
  { value: "image", label: "Image", icon: Image },
];

const MODELS = [
  "mistral-large-latest",
  "mistral-medium-latest",
  "mistral-small-latest",
  "codestral-latest",
  "ministral-3b-latest",
  "ministral-8b-latest",
];

const RESPONSE_FORMATS = [
  { value: "none", label: "Plain Text" },
  { value: "json_object", label: "JSON Object" },
  { value: "json_schema", label: "JSON Schema" },
];

const AGENTS = [
  { value: "news", label: "News Analyst", icon: MagnifyingGlass },
  { value: "sector_predictor", label: "Sector Predictor", icon: Sparkle },
  { value: "stock_recommender", label: "Stock Recommender", icon: Code },
];

const DEFAULT_TOOLS = JSON.stringify(
  [
    {
      type: "function",
      function: {
        name: "get_stock_price",
        description: "Get current stock price for an IDX ticker",
        parameters: {
          type: "object",
          properties: {
            ticker: {
              type: "string",
              description: "The stock ticker symbol on IDX",
            },
          },
          required: ["ticker"],
        },
      },
    },
    {
      type: "function",
      function: {
        name: "get_company_fundamentals",
        description: "Get fundamental ratios (PE, PBV, EPS, DER)",
        parameters: {
          type: "object",
          properties: {
            ticker: {
              type: "string",
              description: "The stock ticker symbol on IDX",
            },
          },
          required: ["ticker"],
        },
      },
    },
  ],
  null,
  2
);

const DEFAULT_INSTRUCTIONS = `Anda adalah analis saham profesional yang berspesialisasi dalam Bursa Efek Indonesia (IHSG).

Tugas Anda:
1. Gunakan tools yang tersedia untuk mendapatkan data saham.
2. Berikan analisis fundamental dan teknikal.
3. Berikan rekomendasi (BUY/HOLD/SELL) beserta reasoning.

Gunakan bahasa Indonesia untuk seluruh output.`;

function ToolCallsLog({ toolCalls }) {
  const [expanded, setExpanded] = useState(false);

  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="mt-3 rounded-lg border border-border">
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:bg-muted/50"
        onClick={() => setExpanded(!expanded)}
        type="button"
      >
        {expanded ? (
          <CaretDown className="h-3 w-3" />
        ) : (
          <CaretRight className="h-3 w-3" />
        )}
        Tool Calls ({toolCalls.length})
      </button>
      {expanded && (
        <div className="space-y-2 border-t border-border px-3 py-2">
          {toolCalls.map((tc, i) => (
            <div
              key={tc.id || i}
              className="rounded bg-muted/50 p-2 font-mono text-[11px]"
            >
              <div className="text-cuan">
                {tc.function.name}
              </div>
              <pre className="mt-1 overflow-x-auto text-muted-foreground">
                {JSON.stringify(JSON.parse(tc.function.arguments || "{}"), null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PlaygroundPanel() {
  const token = localStorage.getItem("ihsg_admin_token");
  const [mode, setMode] = useState("chat");
  const [agentKey, setAgentKey] = useState("news");
  const [capability, setCapability] = useState("none");
  const [model, setModel] = useState("mistral-large-latest");
  const [responseFormat, setResponseFormat] = useState("none");
  const [instructions, setInstructions] = useState(DEFAULT_INSTRUCTIONS);
  const [toolsJson, setToolsJson] = useState(DEFAULT_TOOLS);
  const [toolsError, setToolsError] = useState(null);
  const [temperature, setTemperature] = useState(0.3);
  const [topP, setTopP] = useState(0.9);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [toolCalls, setToolCalls] = useState([]);

  const parseTools = useCallback(() => {
    try {
      const parsed = JSON.parse(toolsJson);
      if (!Array.isArray(parsed)) throw new Error("Tools harus berupa array");
      setToolsError(null);
      return parsed;
    } catch (e) {
      setToolsError(e.message);
      return null;
    }
  }, [toolsJson]);

  const buildResponseFormat = useCallback(() => {
    if (responseFormat === "none") return null;
    if (responseFormat === "json_object") return { type: "json_object" };
    if (responseFormat === "json_schema") {
      return {
        type: "json_schema",
        json_schema: {
          name: "stock_analysis",
          strict: true,
          schema: {
            type: "object",
            properties: {
              ticker: { type: "string" },
              recommendation: { type: "string", enum: ["BUY", "HOLD", "SELL"] },
              confidence_score: { type: "number", minimum: 0, maximum: 100 },
              reasoning: { type: "string" },
            },
            required: ["ticker", "recommendation", "confidence_score", "reasoning"],
            additionalProperties: false,
          },
        },
      };
    }
    return null;
  }, [responseFormat]);

  const handleSend = useCallback(async () => {
    if (!message.trim()) return;

    const newMessages = [...messages, { role: "user", content: message }];
    setMessages(newMessages);
    setMessage("");
    setLoading(true);
    setResult(null);
    setToolCalls([]);

    const body = {};

    if (mode === "agent") {
      body.agent_key = agentKey;
      body.instructions = instructions;
      body.messages = newMessages;
      body.response_format = buildResponseFormat();
    } else {
      const parsedTools = parseTools();
      if (!parsedTools) {
        toast.error("Format JSON tools tidak valid");
        setLoading(false);
        return;
      }
      body.capability = capability;
      body.model = model;
      body.tools = parsedTools;
      body.response_format = buildResponseFormat();
      body.instructions = instructions;
      body.messages = newMessages;
      body.temperature = temperature;
      body.top_p = topP;
    }

    try {
      const resp = await axios.post(
        `${API_BASE}/admin/playground?token=${token}`,
        body
      );

      if (resp.data?.success) {
        const assistantContent = resp.data.content || "(no response)";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: assistantContent },
        ]);
        setResult(resp.data);
        setToolCalls(resp.data.tool_calls || []);
      } else {
        toast.error("Gagal mendapatkan response");
      }
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        "Gagal terhubung ke server";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [
    message,
    messages,
    token,
    capability,
    model,
    instructions,
    temperature,
    topP,
    parseTools,
    buildResponseFormat,
    agentKey,
    mode,
  ]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleReset = useCallback(() => {
    setMessages([]);
    setResult(null);
    setToolCalls([]);
    setMessage("");
  }, []);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Configuration Panel */}
        <div className="space-y-4 lg:col-span-1">
          <Card className="border-border bg-card shadow-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-foreground">
                Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Mode Toggle */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Mode
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  <button
                    className={`flex items-center justify-center gap-1.5 rounded-md border px-2.5 py-1.5 text-[11px] font-medium transition-all ${
                      mode === "chat"
                        ? "border-foreground bg-foreground text-background"
                        : "border-border bg-card text-muted-foreground hover:bg-muted/50"
                    }`}
                    onClick={() => setMode("chat")}
                    type="button"
                  >
                    <ChatText className="h-3 w-3" weight="bold" />
                    Chat Completion
                  </button>
                  <button
                    className={`flex items-center justify-center gap-1.5 rounded-md border px-2.5 py-1.5 text-[11px] font-medium transition-all ${
                      mode === "agent"
                        ? "border-foreground bg-foreground text-background"
                        : "border-border bg-card text-muted-foreground hover:bg-muted/50"
                    }`}
                    onClick={() => setMode("agent")}
                    type="button"
                  >
                    <Robot className="h-3 w-3" weight="bold" />
                    Agent
                  </button>
                </div>
              </div>

              {/* Agent Mode: Pre-created Agent Selector */}
              {mode === "agent" ? (
                <>
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Agent
                    </label>
                    <Select onValueChange={setAgentKey} value={agentKey}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {AGENTS.map((a) => {
                          const Icon = a.icon;
                          return (
                            <SelectItem key={a.value} value={a.value} className="text-xs">
                              <span className="flex items-center gap-2">
                                <Icon className="h-3 w-3" />
                                {a.label}
                              </span>
                            </SelectItem>
                          );
                        })}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Instructions */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Additional Instructions
                    </label>
                    <Textarea
                      className="min-h-[100px] text-xs"
                      onChange={(e) => setInstructions(e.target.value)}
                      placeholder="Optional: tambahkan instruksi tambahan untuk agent"
                      value={instructions}
                    />
                  </div>

                  {/* Response Format */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Response Format
                    </label>
                    <Select onValueChange={setResponseFormat} value={responseFormat}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RESPONSE_FORMATS.map((rf) => (
                          <SelectItem key={rf.value} value={rf.value} className="text-xs">
                            {rf.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                    <p className="text-[11px] text-amber-700">
                      Agent harus dibuat terlebih dahulu di console.mistral.ai.
                      Set agent ID di .env (MISTRAL_AGENT_NEWS_ID, etc.).
                    </p>
                  </div>
                </>
              ) : (
                <>
                  {/* Capability */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Capability
                    </label>
                    <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                      {CAPABILITIES.map((cap) => {
                        const Icon = cap.icon;
                        return (
                          <button
                            key={cap.value}
                            className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-[11px] font-medium transition-all ${
                              capability === cap.value
                                ? "border-foreground bg-foreground text-background"
                                : "border-border bg-card text-muted-foreground hover:bg-muted/50"
                            }`}
                            onClick={() => setCapability(cap.value)}
                            type="button"
                          >
                            <Icon className="h-3 w-3" weight="bold" />
                            {cap.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Model */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Model
                    </label>
                    <Select onValueChange={setModel} value={model}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MODELS.map((m) => (
                          <SelectItem key={m} value={m} className="text-xs">
                            {m}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Response Format */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Response Format
                    </label>
                    <Select onValueChange={setResponseFormat} value={responseFormat}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RESPONSE_FORMATS.map((rf) => (
                          <SelectItem key={rf.value} value={rf.value} className="text-xs">
                            {rf.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Temperature & Top P */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                        Temperature
                      </label>
                      <Input
                        className="h-8 text-xs"
                        max={2}
                        min={0}
                        onChange={(e) => setTemperature(parseFloat(e.target.value) || 0.3)}
                        step={0.1}
                        type="number"
                        value={temperature}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                        Top P
                      </label>
                      <Input
                        className="h-8 text-xs"
                        max={1}
                        min={0}
                        onChange={(e) => setTopP(parseFloat(e.target.value) || 0.9)}
                        step={0.05}
                        type="number"
                        value={topP}
                      />
                    </div>
                  </div>

                  {/* Instructions */}
                  <div className="space-y-1.5">
                    <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Instructions
                    </label>
                    <Textarea
                      className="min-h-[120px] text-xs"
                      onChange={(e) => setInstructions(e.target.value)}
                      value={instructions}
                    />
                  </div>

                  {/* Tools JSON */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                        Tools (JSON)
                      </label>
                      {toolsError && (
                        <span className="text-[10px] text-loss">{toolsError}</span>
                      )}
                    </div>
                    <Textarea
                      className="min-h-[180px] font-mono text-[11px] leading-relaxed"
                      onChange={(e) => setToolsJson(e.target.value)}
                      value={toolsJson}
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Chat Panel */}
        <div className="flex flex-col space-y-4 lg:col-span-2">
          {/* Messages */}
          <Card className="flex min-h-[400px] flex-col border-border bg-card shadow-none">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-semibold text-foreground">
                Chat
              </CardTitle>
              <Button
                className="h-6 text-[10px]"
                disabled={messages.length === 0}
                onClick={handleReset}
                size="sm"
                variant="outline"
              >
                <FloppyDisk className="mr-1 h-3 w-3" />
                Reset
              </Button>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col">
              <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-border bg-muted/30 p-3">
                {messages.length === 0 && (
                  <div className="flex h-full items-center justify-center">
                    <p className="text-center text-xs text-muted-foreground">
                      Kirim pesan untuk memulai playground
                    </p>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
                        msg.role === "user"
                          ? "bg-foreground text-background"
                          : "bg-card text-foreground shadow-sm ring-1 ring-border"
                      }`}
                    >
                      <pre className="whitespace-pre-wrap font-sans text-[13px]">
                        {msg.content}
                      </pre>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-lg bg-card px-3 py-2 shadow-sm ring-1 ring-border">
                      <div className="flex items-center gap-1.5">
                        <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
                        <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: "0.1s" }} />
                        <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: "0.2s" }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Tool Calls Log */}
              <ToolCallsLog toolCalls={toolCalls} />

              {/* Result JSON */}
              {result && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-[11px] font-medium text-muted-foreground hover:text-foreground">
                    Raw Response
                  </summary>
                  <pre className="mt-1 max-h-[200px] overflow-auto rounded-lg bg-foreground p-3 font-mono text-[11px] text-cuan">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </details>
              )}

              {/* Input */}
              <div className="mt-3 flex items-start gap-2">
                <Textarea
                  className="min-h-[44px] flex-1 resize-none text-sm"
                  disabled={loading}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ketik pesan... (Enter untuk kirim)"
                  value={message}
                />
                <Button
                  className="h-[44px] w-[44px] shrink-0"
                  disabled={loading || !message.trim()}
                  onClick={handleSend}
                  size="icon"
                >
                  <PaperPlaneRight className="h-4 w-4" weight="fill" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default PlaygroundPanel;
