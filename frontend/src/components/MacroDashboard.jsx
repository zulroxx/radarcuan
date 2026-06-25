import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowClockwise,
  ArrowElbowDownRight,
  ArrowElbowUpRight,
  ChartLineDown,
  ChartLineUp,
  Coin,
  GlobeHemisphereWest,
  HandCoins,
  Money,
  Scales,
  ShieldCheck,
  ShoppingCartSimple,
  TrendDown,
  TrendUp,
  Wallet,
  WarningCircle,
} from "@phosphor-icons/react";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatCardGrid from "@/components/ui/stat-card-grid";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const ICON_MAP = {
  bi_rate: Coin,
  inflation: TrendDown,
  gdp: GlobeHemisphereWest,
  usd_idr: Coin,
  bond_yield: ChartLineDown,
  cad: ChartLineUp,
  reserves: Money,
  oil_price: TrendUp,
  coal_price: TrendUp,
  cpo_price: TrendUp,
  foreign_flow: ArrowElbowUpRight,
  ihsg: ChartLineUp,
};

const categoryOrder = [
  "Kebijakan Moneter",
  "Pertumbuhan Ekonomi",
  "Nilai Tukar & Komoditas",
  "Aliran Modal",
];

function MacroStatCard({ indicator, icon: Icon }) {
  const change = indicator.change;
  const hasChange = change !== null && change !== undefined;
  const isPositive = hasChange && change >= 0;

  return (
    <Card className="border-border bg-card transition-colors hover:border-muted-foreground/30">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
              <Icon className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">{indicator.label}</p>
              <p className="text-lg font-bold text-foreground">{indicator.value}</p>
            </div>
          </div>
          {hasChange && (
            <div className={`flex items-center gap-0.5 rounded-md px-2 py-0.5 text-xs font-semibold ${
              isPositive
                ? "bg-cuan/10 text-cuan"
                : "bg-loss/10 text-loss"
            }`}>
              {isPositive
                ? <ArrowElbowUpRight className="h-3 w-3" />
                : <ArrowElbowDownRight className="h-3 w-3" />
              }
              {Math.abs(change).toFixed(2)}%
            </div>
          )}
        </div>
        <div className="mt-2 flex items-center justify-between">
          <p className="text-[10px] leading-4 text-muted-foreground">{indicator.description}</p>
          {indicator.source && (
            <p className="shrink-0 text-[9px] text-muted-foreground/50">{indicator.source}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function MacroDashboard() {
  const [indicators, setIndicators] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cachedAt, setCachedAt] = useState(null);

  const fetchData = useCallback(async ({ refresh = false } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE}/macro/indicators`, {
        params: { refresh },
      });
      if (response.data.success) {
        setIndicators(response.data.indicators || []);
        setCachedAt(response.data.cached_at);
      } else {
        setError("Gagal memuat data makro ekonomi");
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Terjadi kesalahan jaringan";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const grouped = useMemo(() => {
    const map = {};
    for (const cat of categoryOrder) {
      map[cat] = [];
    }
    for (const ind of indicators) {
      const cat = ind.category || "Lainnya";
      if (!map[cat]) map[cat] = [];
      map[cat].push(ind);
    }
    return map;
  }, [indicators]);

  const filteredCategories = useMemo(() => {
    return categoryOrder.filter((cat) => (grouped[cat] || []).length > 0);
  }, [grouped]);

  const macroStatus = useMemo(() => {
    const getNum = (id) => {
      const found = indicators.find((i) => i.id === id);
      if (!found) return null;
      const raw = found.value?.replace(/[^0-9.,\-]/g, "").replace(",", ".");
      return raw ? parseFloat(raw) : null;
    };

    const biRate = getNum("bi_rate");
    const inflation = getNum("inflation");
    const usdIdr = getNum("usd_idr");
    const gdp = getNum("gdp");

    const mengetatScore =
      (biRate !== null && biRate > 5.75 ? 1 : 0) +
      (inflation !== null && inflation > 3.5 ? 1 : 0) +
      (usdIdr !== null && usdIdr > 16500 ? 1 : 0);

    const lesuScore =
      (gdp !== null && gdp < 4.5 ? 1 : 0) +
      (inflation !== null && inflation > 5 ? 1 : 0);

    if (mengetatScore >= 2) return "mengetat";
    if (lesuScore >= 2) return "lesu";
    return "stabil";
  }, [indicators]);

  const periodLabel = useMemo(() => {
    const months = [
      "Januari", "Februari", "Maret", "April", "Mei", "Juni",
      "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ];
    const now = new Date();
    const month = months[now.getMonth()];
    const year = now.getFullYear();
    const quarter = Math.floor(now.getMonth() / 3) + 1;
    return `${month} ${year} / Kuartal ${quarter} ${year}`;
  }, []);

  const rpkContent = useMemo(() => {
    const templates = {
      mengetat: {
        label: "Ekonomi Mengetat",
        badge: "bg-amber-500/10 text-amber-600 border-amber-500/20",
        situation: {
          kondisi:
            "Inflasi masih di atas target, nilai tukar Rupiah tertekan, dan suku bunga acuan BI berada di level tinggi. Likuiditas pasar mengetat seiring kebijakan moneter yang agresif untuk mengendalikan inflasi.",
          dampak:
            "Biaya pinjaman (KPR, kredit kendaraan, modal usaha) meningkat. Harga kebutuhan pokok masih tinggi. Daya beli masyarakat menengah ke bawah tergerus. Margin bisnis tertekan oleh biaya operasional yang naik.",
        },
        actions: {
          belanja: {
            lakukan: "Prioritaskan belanja kebutuhan primer. Manfaatkan promo & diskon untuk stok barang tahan lama. Beralih ke produk substitusi yang lebih murah.",
            tunda: "Tunda pembelian barang impor, gadget terbaru, renovasi rumah non-darurat, dan liburan ke luar negeri.",
          },
          utang: {
            kebijakanBaru: "Hindari mengambil utang konsumtif baru (KTA, paylater, kartu kredit). Jika mendesak, pilih utang dengan suku bunga tetap (fixed rate).",
            strategiBerjalan: "Alihkan cicilan ke tenor lebih panjang jika memungkinkan. Lunasi utang berbunga tertinggi terlebih dahulu. Hindari minimal payment kartu kredit.",
          },
          investasi: {
            kurangi: "Kurangi porsi saham siklikal (properti, otomotif, ritel) dan aset kripto. Waspada terhadap obligasi jangka panjang saat suku bunga naik.",
            tambah: "Tambah porsi SBN (Surat Berharga Negara) dengan kupon tinggi, deposito, dan instrumen pasar uang. Saham sektor perbankan & barang pokok relatif defensif.",
          },
          safety: {
            danaDarurat: "Target dana darurat setara 6–12 bulan pengeluaran rutin, simpan di rekening terpisah yang likuid (deposito cair / money market).",
            proteksi: "Pastikan asuransi kesehatan aktif. Cari sumber pendapatan tambahan (side hustle / freelance). Evaluasi ulang portofolio investasi setiap 1–2 bulan.",
          },
        },
      },
      stabil: {
        label: "Ekonomi Stabil",
        badge: "bg-cuan/10 text-cuan border-cuan/20",
        situation: {
          kondisi:
            "Inflasi terkendali dalam target, nilai tukar Rupiah relatif stabil, dan suku bunga acuan di level yang mendukung pertumbuhan. Likuiditas pasar terjaga dengan baik.",
          dampak:
            "Biaya pinjaman masih terkendali. Daya beli masyarakat cukup terjaga. Lingkungan usaha kondusif untuk ekspansi ringan. Peluang investasi di berbagai sektor terbuka.",
        },
        actions: {
          belanja: {
            lakukan: "Lakukan belanja sesuai prioritas dan anggaran. Manfaatkan momen promo untuk pembelian barang kebutuhan. Alokasikan dana untuk pengembangan diri (kursus, sertifikasi).",
            tunda: "Tetap hindari belanja impulsif. Evaluasi ulang pengeluaran langganan yang tidak terpakai (subscription).",
          },
          utang: {
            kebijakanBaru: "Utang produktif diperbolehkan (KPR, kredit usaha) dengan simulasi arus kas yang ketat. Batasi utang konsumtif maksimal 30% dari pendapatan.",
            strategiBerjalan: "Jaga rasio cicilan terhadap pendapatan di bawah 35%. Lakukan pembayaran tepat waktu untuk menjaga skor kredit. Pertimbangkan refinancing jika ada penawaran bunga lebih rendah.",
          },
          investasi: {
            kurangi: "Kurangi porsi kas berlebih (>20% portofolio). Kurangi eksposur pada aset berisiko tinggi tanpa fundamental (spekulasi kripto, saham gorengan).",
            tambah: "Tambah porsi reksa dana saham & obligasi secara proporsional. Akumulasi saham blue-chip dengan valuasi wajar. SBN tetap menjadi pilihan aman untuk porsi defensif.",
          },
          safety: {
            danaDarurat: "Pertahankan dana darurat setara 6 bulan pengeluaran. Evaluasi kecukupan dana darurat setiap 3 bulan.",
            proteksi: "Pastikan asuransi jiwa & kesehatan sesuai tanggungan. Diversifikasi sumber pendapatan. Review portofolio setiap kuartal.",
          },
        },
      },
      lesu: {
        label: "Ekonomi Lesu",
        badge: "bg-loss/10 text-loss border-loss/20",
        situation: {
          kondisi:
            "Pertumbuhan ekonomi melambat di bawah potensi, daya beli masyarakat lemah, dan sektor usaha mengalami kontraksi. Risiko PHK meningkat seiring perlambatan permintaan.",
          dampak:
            "Pendapatan menurun atau tidak stabil. Peluang kerja semakin terbatas. Bisnis mengalami penurunan omzet. Harga aset (rumah, saham) cenderung turun. Risiko gagal bayar utang meningkat.",
        },
        actions: {
          belanja: {
            lakukan: "Fokus 100% pada kebutuhan primer. Cari alternatif lebih murah untuk setiap pengeluaran. Manfaatkan program bantuan sosial & subsidi pemerintah.",
            tunda: "Hentikan semua belanja non-esensial. Tunda pembelian aset besar seperti mobil, rumah, atau renovasi. Jangan gunakan tabungan untuk konsumsi rutin.",
          },
          utang: {
            kebijakanBaru: "LARANGAN mengambil utang baru kecuali darurat medis. Jika terpaksa ambil utang, pastikan ada arus kas masuk yang jelas.",
            strategiBerjalan: "Prioritaskan pelunasan utang terkecil (snowball method) untuk kurangi beban. Negosiasi restrukturisasi utang dengan bank jika kesulitan bayar. Hindari pinjaman online ilegal.",
          },
          investasi: {
            kurangi: "Kurangi hampir semua posisi saham, alihkan ke instrumen aman. Hindari investasi jangka panjang yang tidak likuid. Jangan melakukan margin trading / utang untuk investasi.",
            tambah: "Tambah porsi kas & deposito. Emas sebagai safe haven untuk lindung nilai. Hanya investasi pada SBN yang dijamin pemerintah. Tunggu sinyal pemulihan sebelum masuk pasar saham.",
          },
          safety: {
            danaDarurat: "Tingkatkan dana darurat menjadi 12+ bulan pengeluaran. Jangan simpan di aset berisiko. Utamakan likuiditas di atas imbal hasil.",
            proteksi: "Pastikan asuransi jiwa & kesehatan tetap aktif (jangan ditunggak). Siapkan CV & portofolio untuk antisipasi PHK. Cari pendapatan alternatif (ojol, freelance, dagang kecil). Jual aset non-produktif untuk tambah kas.",
          },
        },
      },
    };
    return templates[macroStatus] || templates.stabil;
  }, [macroStatus]);

  function RpkSection() {
    return (
      <Card className="border-border bg-card">
        <CardHeader className="border-b border-border p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
              <Scales className="h-4 w-4 text-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                RINGKASAN PENGAMBILAN KEPUTUSAN (RPK) FINANSIAL
              </p>
              <p className="text-sm text-muted-foreground">
                Periode Analisis: <span className="font-semibold text-foreground">{periodLabel}</span>
              </p>
            </div>
            <Badge className={`ml-auto gap-1.5 border px-3 py-1 text-xs font-semibold ${rpkContent.badge}`}>
              {rpkContent.label}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-5 p-4 sm:p-5">
          <div>
            <h4 className="flex items-center gap-2 text-sm font-bold text-foreground">
              <GlobeHemisphereWest className="h-4 w-4 text-chart-1" />
              1. KONDISI PEMICU & DAMPAK LANGSUNG
            </h4>
            <div className="mt-3 space-y-3">
              <div className="rounded-lg border border-chart-1/20 bg-chart-1/5 p-3">
                <p className="text-xs font-semibold text-chart-1">Kondisi Pasar Terkini</p>
                <p className="mt-1 text-xs leading-6 text-muted-foreground">
                  {rpkContent.situation.kondisi}
                </p>
              </div>
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                <p className="text-xs font-semibold text-amber-600">Dampak Pada Dompet / Bisnis</p>
                <p className="mt-1 text-xs leading-6 text-amber-600/80">
                  {rpkContent.situation.dampak}
                </p>
              </div>
            </div>
          </div>

          <div>
            <h4 className="flex items-center gap-2 text-sm font-bold text-foreground">
              <ChartLineUp className="h-4 w-4 text-cuan" />
              2. MATRIKS KEPUTUSAN AKSI
            </h4>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <Card className="border-border bg-card shadow-none">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-chart-1/10">
                      <ShoppingCartSimple className="h-3.5 w-3.5 text-chart-1" />
                    </div>
                    <p className="text-xs font-bold text-foreground">Kebijakan Belanja & Konsumsi</p>
                  </div>
                  <div className="mt-3 space-y-2">
                    <div className="rounded-md border border-cuan/20 bg-cuan/10 p-2.5">
                      <p className="flex items-center gap-1 text-[10px] font-semibold text-cuan">
                        <ArrowElbowUpRight className="h-3 w-3" weight="bold" />
                        LAKUKAN
                      </p>
                      <p className="mt-0.5 text-[11px] leading-5 text-muted-foreground">
                        {rpkContent.actions.belanja.lakukan}
                      </p>
                    </div>
                    <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2.5">
                      <p className="flex items-center gap-1 text-[10px] font-semibold text-amber-600">
                        <ArrowElbowDownRight className="h-3 w-3" weight="bold" />
                        TUNDA / BATASI
                      </p>
                      <p className="mt-0.5 text-[11px] leading-5 text-amber-600/80">
                        {rpkContent.actions.belanja.tunda}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border bg-card shadow-none">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-loss/10">
                      <Wallet className="h-3.5 w-3.5 text-loss" />
                    </div>
                    <p className="text-xs font-bold text-foreground">Manajemen Utang & Kredit</p>
                  </div>
                  <div className="mt-3 space-y-2">
                    <div className="rounded-md border border-loss/20 bg-loss/5 p-2.5">
                      <p className="flex items-center gap-1 text-[10px] font-semibold text-loss">
                        <WarningCircle className="h-3 w-3" weight="bold" />
                        Kebijakan Utang Baru
                      </p>
                      <p className="mt-0.5 text-[11px] leading-5 text-muted-foreground">
                        {rpkContent.actions.utang.kebijakanBaru}
                      </p>
                    </div>
                    <div className="rounded-md border border-border bg-muted/30 p-2.5">
                      <p className="flex items-center gap-1 text-[10px] font-semibold text-foreground">
                        <ArrowClockwise className="h-3 w-3" weight="bold" />
                        Strategi Utang Berjalan
                      </p>
                      <p className="mt-0.5 text-[11px] leading-5 text-muted-foreground">
                        {rpkContent.actions.utang.strategiBerjalan}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border bg-card shadow-none">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cuan/10">
                      <HandCoins className="h-3.5 w-3.5 text-cuan" />
                    </div>
                    <p className="text-xs font-bold text-foreground">Alokasi Investasi & Aset</p>
                  </div>
                  <div className="mt-3 space-y-2">
                    <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-2.5">
                      <p className="flex items-center gap-1 text-[10px] font-semibold text-amber-600">
                        <TrendDown className="h-3 w-3" weight="bold" />
                        Kurangi Porsi Pada
                      </p>
                      <p className="mt-0.5 text-[11px] leading-5 text-amber-600/80">
                        {rpkContent.actions.investasi.kurangi}
                      </p>
                    </div>
                    <div className="rounded-md border border-cuan/20 bg-cuan/10 p-2.5">
                      <p className="flex items-center gap-1 text-[10px] font-semibold text-cuan">
                        <TrendUp className="h-3 w-3" weight="bold" />
                        Tambah Porsi Pada
                      </p>
                      <p className="mt-0.5 text-[11px] leading-5 text-muted-foreground">
                        {rpkContent.actions.investasi.tambah}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          <div>
            <h4 className="flex items-center gap-2 text-sm font-bold text-foreground">
              <ShieldCheck className="h-4 w-4 text-cuan" />
              3. JARING PENGAMAN & CADANGAN RISIKO
            </h4>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-cuan/20 bg-cuan/10 p-3">
                <p className="flex items-center gap-1.5 text-xs font-semibold text-cuan">
                  <Money className="h-3.5 w-3.5" />
                  Target Dana Darurat
                </p>
                <p className="mt-1 text-xs leading-6 text-muted-foreground">
                  {rpkContent.actions.safety.danaDarurat}
                </p>
              </div>
              <div className="rounded-lg border border-chart-1/20 bg-chart-1/5 p-3">
                <p className="flex items-center gap-1.5 text-xs font-semibold text-chart-1">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Langkah Proteksi Tambahan
                </p>
                <p className="mt-1 text-xs leading-6 text-muted-foreground">
                  {rpkContent.actions.safety.proteksi}
                </p>
              </div>
            </div>
          </div>

          <p className="text-center text-[10px] text-muted-foreground">
            RPK Finansial bersifat informatif dan edukatif, bukan konsultasi investasi terpersonalisasi.
            Keputusan tetap sepenuhnya di tangan Anda.
          </p>
        </CardContent>
      </Card>
    );
  }

  const statItems = useMemo(() => {
    const total = indicators.length;
    let positive = 0;
    let negative = 0;
    let sumChange = 0;
    let changeCount = 0;
    for (const ind of indicators) {
      if (ind.change !== null && ind.change !== undefined) {
        if (ind.change >= 0) positive++;
        else negative++;
        sumChange += ind.change;
        changeCount++;
      }
    }
    const avgChange = changeCount > 0 ? sumChange / changeCount : 0;
    return [
      { label: "Total Indikator", value: total, description: "Semua kategori", icon: GlobeHemisphereWest },
      { label: "Positif", value: positive, description: "Indikator menguat", icon: TrendUp },
      { label: "Negatif", value: negative, description: "Indikator melemah", icon: TrendDown },
      { label: "Rata-rata Perubahan", value: `${avgChange >= 0 ? "+" : ""}${avgChange.toFixed(2)}%`, description: "Periode terakhir", icon: ChartLineUp },
    ];
  }, [indicators]);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            Makro Ekonomi
          </p>
          <h2 className="mt-1.5 text-lg font-semibold text-foreground sm:text-xl">
            Indikator Ekonomi Makro Indonesia
          </h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground sm:text-sm">
            Data real-time dari Yahoo Finance dan sumber terbuka. Indikator
            fundamental diperbarui berdasarkan rilis resmi BI & BPS.
          </p>
        </div>
        <Button
          className="shrink-0"
          disabled={loading}
          onClick={() => fetchData({ refresh: true })}
          size="sm"
          variant="outline"
        >
          <ArrowClockwise className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <StatCardGrid items={statItems} columns={4} />

      {loading && indicators.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <ArrowClockwise className="h-6 w-6 animate-spin text-muted-foreground" />
          <p className="mt-3 text-sm text-muted-foreground">Memuat data makro ekonomi...</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-16">
          <WarningCircle className="h-8 w-8 text-loss" />
          <p className="mt-3 text-sm font-medium text-foreground">Gagal memuat data</p>
          <p className="mt-1 text-xs text-muted-foreground">{error}</p>
          <Button className="mt-4" onClick={() => fetchData({ refresh: true })} variant="outline">
            <ArrowClockwise className="mr-2 h-4 w-4" />
            Coba Lagi
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          {indicators.length > 0 && <RpkSection />}

          {filteredCategories.map((cat) => {
            const catIndicators = grouped[cat] || [];
            return (
              <div key={cat}>
                <h3 className="mb-3 text-sm font-semibold text-foreground">
                  {cat}
                </h3>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {catIndicators.map((indicator) => (
                    <MacroStatCard
                      key={indicator.id}
                      icon={ICON_MAP[indicator.id] || Coin}
                      indicator={indicator}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="rounded-lg border border-border bg-muted/30 p-3 sm:p-4">
        <div className="flex items-start gap-3">
          <Coin className="mt-0.5 hidden h-5 w-5 shrink-0 text-muted-foreground sm:block" />
          <div className="min-w-0 space-y-1">
            <p className="text-xs font-semibold text-foreground sm:text-sm">
              Disclaimer Makro Ekonomi
            </p>
            <p className="text-xs leading-6 text-muted-foreground sm:text-sm">
              Data indikator makro bersifat indikatif dan merupakan estimasi
              berdasarkan sumber terbuka. Untuk data real-time dan akurat,
              rujuk publikasi resmi Bank Indonesia, BPS, dan Kementerian
              Keuangan. Data diperbarui secara periodik dan tidak untuk
              dijadikan dasar keputusan investasi tunggal.
            </p>
          </div>
        </div>
      </div>

      <p className="text-center text-[10px] text-muted-foreground">
        {cachedAt
          ? `Terakhir diperbarui: ${new Date(cachedAt).toLocaleString("id-ID")}`
          : "Memuat..."}
        {" — "}Data fundamental diperbarui sesuai rilis resmi, data pasar real-time via Yahoo Finance
      </p>
    </div>
  );
}
