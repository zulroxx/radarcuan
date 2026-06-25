import { Sparkle } from "@phosphor-icons/react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import useScreenerData from "@/hooks/useScreenerData";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");

function PremiumWaitlistCard({ onWaitlistChange, onWaitlistSubmit, waitlistForm, waitlistLoading }) {
  return (
    <Card className="overflow-hidden border-none bg-foreground text-primary-foreground" data-testid="premium-waitlist-card">
      <CardContent className="space-y-4 p-5">
        <div className="inline-flex w-fit items-center gap-2 rounded-md bg-white/10 px-3 py-1 text-xs font-medium text-primary-foreground" data-testid="premium-waitlist-badge">
          <Sparkle className="h-3.5 w-3.5 text-cuan" weight="fill" />
          Premium Waitlist
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-primary-foreground" data-testid="premium-waitlist-title">Ingin Proyeksi Laba Berbasis AI & Analisis Sektoral Mendalam?</h3>
          <p className="text-sm leading-6 text-muted-foreground" data-testid="premium-waitlist-description">Gabung waitlist premium kami untuk akses lebih awal saat modul proyeksi, sector intelligence, dan ranking tematik siap dirilis.</p>
        </div>
        <form autoComplete="on" className="space-y-3" onSubmit={onWaitlistSubmit}>
          <Input className="border-white/15 bg-white/10 text-primary-foreground placeholder:text-muted-foreground" data-testid="premium-waitlist-email-input" id="premium-email" name="email" autoComplete="email" onChange={onWaitlistChange} placeholder="nama@email.com" type="email" value={waitlistForm.email} />
          <Textarea className="min-h-[80px] border-white/15 bg-white/10 text-primary-foreground placeholder:text-muted-foreground" data-testid="premium-waitlist-note-input" id="premium-note" name="note" onChange={onWaitlistChange} placeholder="Sektor atau ide riset yang ingin Anda lihat" value={waitlistForm.note} />
          <Button className="w-full bg-cuan text-primary-foreground hover:bg-cuan/90" data-testid="premium-waitlist-submit-button" disabled={waitlistLoading} type="submit">
            {waitlistLoading ? "Menyimpan..." : "Daftar Waitlist Premium"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function FilterSidebar() {
  const { waitlistForm, handleWaitlistChange, submitWaitlist, waitlistLoading } = useScreenerData(`${BACKEND_URL}/api`);

  return (
    <aside className="w-full">
      <PremiumWaitlistCard onWaitlistChange={handleWaitlistChange} onWaitlistSubmit={submitWaitlist} waitlistForm={waitlistForm} waitlistLoading={waitlistLoading} />
    </aside>
  );
}
