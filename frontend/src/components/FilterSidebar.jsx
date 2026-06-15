import { Sparkle } from "@phosphor-icons/react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const WAITLIST_CARD_STYLE = {
  backgroundImage: "linear-gradient(180deg, rgba(15,23,42,0.78), rgba(15,23,42,0.96)), url(https://images.unsplash.com/photo-1644088379091-d574269d422f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGRhcmslMjBibHVlJTIwZmluYW5jaWFsJTIwZGF0YXxlbnwwfHx8fDE3ODEzNjY0Mjl8MA&ixlib=rb-4.1.0&q=85)",
  backgroundPosition: "center",
  backgroundSize: "cover",
};

function PremiumWaitlistCard({ onWaitlistChange, onWaitlistSubmit, waitlistForm, waitlistLoading }) {
  return (
    <Card className="overflow-hidden border-none bg-slate-950 text-white shadow-[0_24px_70px_rgba(15,23,42,0.22)]" data-testid="premium-waitlist-card" style={WAITLIST_CARD_STYLE}>
      <CardContent className="space-y-4 p-6">
        <div className="inline-flex w-fit items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white" data-testid="premium-waitlist-badge">
          <Sparkle className="h-3.5 w-3.5 text-emerald-400" weight="fill" />
          Premium Waitlist
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-semibold" data-testid="premium-waitlist-title">Ingin Proyeksi Laba Berbasis AI & Analisis Sektoral Mendalam?</h3>
          <p className="text-sm leading-6 text-slate-300" data-testid="premium-waitlist-description">Gabung waitlist premium kami untuk akses lebih awal saat modul proyeksi, sector intelligence, dan ranking tematik siap dirilis.</p>
        </div>
        <form className="space-y-3" onSubmit={onWaitlistSubmit}>
          <Input className="border-white/15 bg-white/10 text-white placeholder:text-slate-300" data-testid="premium-waitlist-email-input" name="email" onChange={onWaitlistChange} placeholder="nama@email.com" type="email" value={waitlistForm.email} />
          <Textarea className="min-h-[88px] border-white/15 bg-white/10 text-white placeholder:text-slate-300" data-testid="premium-waitlist-note-input" name="note" onChange={onWaitlistChange} placeholder="Sektor atau ide riset yang ingin Anda lihat" value={waitlistForm.note} />
          <Button className="w-full rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400" data-testid="premium-waitlist-submit-button" disabled={waitlistLoading} type="submit">
            {waitlistLoading ? "Menyimpan..." : "Daftar Waitlist Premium"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function FilterSidebar({
  waitlistForm,
  onWaitlistChange,
  onWaitlistSubmit,
  waitlistLoading,
}) {
  return (
    <aside className="w-full lg:sticky lg:top-[97px] lg:max-h-[calc(100vh-116px)] lg:w-80 lg:overflow-y-auto">
      <PremiumWaitlistCard onWaitlistChange={onWaitlistChange} onWaitlistSubmit={onWaitlistSubmit} waitlistForm={waitlistForm} waitlistLoading={waitlistLoading} />
    </aside>
  );
}
