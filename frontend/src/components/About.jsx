import {
  ChartLineUp,
  Clock,
  GlobeHemisphereWest,
  Kanban,
  MagnifyingGlass,
  Newspaper,
  Robot,
  ShieldCheck,
  Sparkle,
  TrendUp,
} from "@phosphor-icons/react";
import { Card, CardContent } from "@/components/ui/card";

const STATS = [
  { label: "Saham IHSG", value: "700+", desc: "Data real-time harga, volume & rasio fundamental" },
  { label: "Sektor IDX", value: "12", desc: "Analisis AI per sektor dengan confidence score" },
  { label: "AI Model", value: "Mistral", desc: "Prediksi return & rekomendasi saham cerdas" },
  { label: "Update Otomatis", value: "4 Jam", desc: "Data selalu segar tanpa refresh manual" },
];

const STEPS = [
  {
    icon: MagnifyingGlass,
    title: "Screener TradingView",
    desc: "Mengambil data 700+ saham IHSG — harga, volume, rasio fundamental (PER, PBV, ROE, dividend yield) melalui custom screen dan menyimpannya ke cache.",
  },
  {
    icon: Robot,
    title: "AI Agent (Mistral AI)",
    desc: "Menganalisis data sektoral dan fundamental untuk menghasilkan prediksi return, rekomendasi saham, serta analisis sentimen berita secara otomatis.",
  },
  {
    icon: Clock,
    title: "Scheduler Otomatis",
    desc: "Semua data diperbarui setiap 4 jam di latar belakang. Tidak perlu intervensi pengguna — sistem berjalan mandiri dan selalu siap pakai.",
  },
  {
    icon: Sparkle,
    title: "Penyajian Instan",
    desc: "Data sudah siap dari cache saat halaman dibuka. Jika data belum tersedia, sistem memicu pembaruan dan memberi notifikasi real-time.",
  },
];

const SOURCES = [
  {
    icon: GlobeHemisphereWest,
    name: "TradingView Screener",
    desc: "Data real-time harga, volume, dan rasio fundamental (PER, PBV, ROE, dividend yield) dari 700+ saham IHSG melalui custom screen.",
  },
  {
    icon: TrendUp,
    name: "Yahoo Finance (yfinance)",
    desc: "Harga historis, data makroekonomi (IHSG, USD/IDR, minyak, S&P 500, Nikkei, HSI), serta laporan keuangan fundamental emiten.",
  },
  {
    icon: Robot,
    name: "Mistral AI",
    desc: "Analisis sektoral, rekomendasi saham, dan sentimen berita menggunakan LLM Mistral AI (mistral-small-latest) tanpa fine-tuning.",
  },
  {
    icon: Sparkle,
    name: "Scheduler Otomatis",
    desc: "Semua data diperbarui setiap 4 jam secara background. Tidak perlu refresh manual — sistem siap pakai kapan pun.",
  },
];

const FEATURES = [
  {
    icon: MagnifyingGlass,
    title: "Screener IHSG",
    desc: "Filter 700+ saham berdasarkan rasio fundamental, scoring AI, dan rekomendasi. 11 kolom lengkap selalu terlihat di semua ukuran layar.",
  },
  {
    icon: ChartLineUp,
    title: "Prediksi Sektor",
    desc: "AI menganalisis 12 sektor IDX untuk 4 timeframe (1, 3, 6, 12 bulan) dengan confidence score, key drivers, dan macro context.",
  },
  {
    icon: TrendUp,
    title: "Rekomendasi Saham",
    desc: "Setiap sektor memiliki 10 rekomendasi saham teratas lengkap dengan scoring fundamental, valuasi, dan sentimen berita.",
  },
  {
    icon: Kanban,
    title: "Order Book Simulation",
    desc: "Simulasi beli/jual berdasarkan #1 sektor dan top 2 emiten, lengkap dengan estimasi return dan aktual return dari pergerakan harga pasar.",
  },
  {
    icon: Newspaper,
    title: "Berita & Sentimen",
    desc: "Analisis berita pasar terbaru dengan klasifikasi sentimen positif/netral/negatif oleh AI.",
  },
  {
    icon: GlobeHemisphereWest,
    title: "Makro Ekonomi",
    desc: "Indikator makro: IHSG, USD/IDR, harga minyak, S&P 500, Nikkei 225, dan Hang Seng dalam satu dashboard.",
  },
];

export default function About() {
  return (
    <div className="space-y-14">
      {/* Hero */}
      <section>
        <div className="grid gap-8 lg:grid-cols-[1.3fr_0.7fr] lg:gap-12">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100">
                <ChartLineUp className="h-7 w-7 text-emerald-600" weight="duotone" />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-600">
                  PLATFORM ANALISIS SAHAM
                </p>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                  Tentang RadarCuan
                </h1>
              </div>
            </div>
            <p className="max-w-xl text-sm leading-7 text-slate-600 sm:text-base">
              RadarCuan adalah platform screening dan analisis saham IHSG yang menggabungkan data pasar real-time
              dengan kecerdasan buatan untuk memberikan rekomendasi sektor dan saham yang lebih cerdas.
              Semua data dikumpulkan secara otomatis setiap 4 jam — Anda tidak perlu menunggu atau me-refresh halaman.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {STATS.map((s) => (
              <Card key={s.label} className="border-slate-200 bg-white shadow-none">
                <CardContent className="space-y-1 p-3 sm:p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    {s.label}
                  </p>
                  <p className="text-xl font-semibold text-slate-950 sm:text-2xl">
                    {s.value}
                  </p>
                  <p className="text-[11px] leading-4 text-slate-400">
                    {s.desc}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Cara Kerja */}
      <section>
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-600">
            ALUR KERJA
          </p>
          <h2 className="text-lg font-semibold text-slate-950 sm:text-xl">
            Bagaimana RadarCuan Bekerja?
          </h2>
          <p className="text-xs leading-6 text-slate-600 sm:text-sm">
            Dari pengambilan data hingga penyajian instan — semuanya berjalan otomatis di latar belakang.
          </p>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {STEPS.map((step, i) => (
            <Card key={step.title} className="border-slate-200 bg-white shadow-none">
              <CardContent className="flex gap-4 p-4">
                <div className="flex flex-col items-center gap-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100">
                    <step.icon className="h-5 w-5 text-emerald-600" weight="duotone" />
                  </div>
                  <span className="text-[11px] font-bold text-slate-300">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-800">{step.title}</p>
                  <p className="mt-1 text-xs leading-6 text-slate-500">{step.desc}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Sumber Data */}
      <section>
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-600">
            DATA & TEKNOLOGI
          </p>
          <h2 className="text-lg font-semibold text-slate-950 sm:text-xl">
            Sumber Data
          </h2>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {SOURCES.map((source) => (
            <Card
              key={source.name}
              className="border-slate-200 bg-white shadow-none transition-all duration-200 hover:shadow-md"
            >
              <CardContent className="flex gap-4 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-50">
                  <source.icon className="h-5 w-5 text-emerald-600" weight="duotone" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{source.name}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{source.desc}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Fitur Utama */}
      <section>
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-600">
            FITUR PLATFORM
          </p>
          <h2 className="text-lg font-semibold text-slate-950 sm:text-xl">
            Fitur Utama
          </h2>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card
              key={feature.title}
              className="border-slate-200 bg-white shadow-none transition-all duration-200 hover:shadow-md"
            >
              <CardContent className="p-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50">
                  <feature.icon className="h-4 w-4 text-emerald-600" weight="duotone" />
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-800">{feature.title}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">{feature.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Disclaimer */}
      <section>
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 sm:p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 hidden h-5 w-5 shrink-0 text-emerald-700 sm:block" weight="fill" />
            <div className="min-w-0 space-y-2">
              <p className="text-xs font-semibold text-emerald-950 sm:text-sm">Disclaimer</p>
              <p className="text-xs leading-6 text-emerald-800 sm:text-sm">
                RadarCuan adalah platform analisis dan screening saham yang menggunakan AI untuk memberikan wawasan tambahan.
                Seluruh data dan rekomendasi bersifat informasional dan bukan merupakan saran investasi, ajakan,
                atau rekomendasi untuk membeli atau menjual sekuritas tertentu. Keputusan investasi sepenuhnya
                berada di tangan pengguna. Tidak ada jaminan keakuratan, kelengkapan, atau ketepatan data.
                Gunakan dengan bijak dan selalu lakukan riset mandiri sebelum berinvestasi.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <section>
        <div className="border-t border-slate-200 pt-6">
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
            <p className="text-xs text-slate-400">
              RadarCuan v0.1
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {["React", "FastAPI", "MongoDB", "Mistral AI", "TradingView", "Yahoo Finance"].map((tech) => (
                <span
                  key={tech}
                  className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-500"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
