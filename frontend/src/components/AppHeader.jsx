import { useState } from "react";
import {
  GlobeHemisphereWest,
  Info,
  List,
  LockKey,
  MagnifyingGlass,
  Scroll,
  Sparkle,
  X,
} from "@phosphor-icons/react";
import { NavLink, useLocation } from "react-router-dom";
import FeedbackDialog from "@/components/FeedbackDialog";
import ProcessingStatus from "@/components/ProcessingStatus";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { SCREENER } from "@/constants/testIds";

const linkClass = ({ isActive }) =>
  `flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors ${
    isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
  }`;

const navItems = [
  { to: "/", icon: MagnifyingGlass, label: "Screener", desc: "Screen saham IHSG" },
  { to: "/prediction", icon: Sparkle, label: "Agent Prediksi", desc: "Prediksi sektor & rekomendasi" },
  { to: "/order-book", icon: Scroll, label: "Order Book", desc: "Simulasi historis order" },
  { to: "/macro", icon: GlobeHemisphereWest, label: "Makro Ekonomi", desc: "Indikator ekonomi makro" },
  { to: "/about", icon: Info, label: "Tentang", desc: "Info & sumber data RadarCuan" },
  { to: "/admin", icon: LockKey, label: "Admin", desc: "Panel admin" },
];

export default function AppHeader() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const { pathname } = useLocation();

  function handleNavClick() {
    setSheetOpen(false);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-md" data-testid={SCREENER.header}>
      <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-2 px-4 py-2 sm:px-6 lg:px-8">
        {/* Brand + Desktop nav */}
        <div className="flex items-center gap-4 sm:gap-6">
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-foreground sm:text-lg lg:text-xl" data-testid={SCREENER.heroTitle}>
              RadarCuan
            </h1>
            <Badge className="border-border bg-muted px-1.5 py-0 text-[10px] font-semibold text-muted-foreground" variant="outline">
              Beta
            </Badge>
          </div>

          {/* Desktop nav */}
          <nav className="hidden md:flex md:gap-0.5">
            {navItems.map((item) => (
              <NavLink key={item.to} className={linkClass} to={item.to}>
                <item.icon className="h-3.5 w-3.5 shrink-0" />
                <span className="hidden lg:inline">{item.label}</span>
                <span className="lg:hidden">{item.label.replace("Agent ", "").replace("Makro ", "")}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right side */}
        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
          <ProcessingStatus />
          <FeedbackDialog />
          {/* Mobile hamburger */}
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button className="md:hidden" size="icon" variant="ghost">
                <List className="h-4 w-4" />
                <span className="sr-only">Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent className="flex w-72 flex-col gap-0 p-0" side="right">
              <SheetTitle className="sr-only">Navigasi</SheetTitle>
              <SheetDescription className="sr-only">Menu navigasi RadarCuan</SheetDescription>

              {/* Header sidebar */}
              <div className="flex items-center justify-between border-b border-border px-4 py-3">
                <span className="text-xs font-semibold text-muted-foreground">Menu</span>
                <SheetTrigger asChild>
                  <Button className="-mr-1 h-6 w-6" size="icon" variant="ghost">
                    <X className="h-3.5 w-3.5" />
                    <span className="sr-only">Tutup</span>
                  </Button>
                </SheetTrigger>
              </div>

              {/* Nav items */}
              <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.to;
                  return (
                    <NavLink
                      key={item.to}
                      className={`flex items-center gap-3 rounded-md px-3 py-2.5 transition-colors ${
                        isActive
                          ? "bg-accent text-accent-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      }`}
                      to={item.to}
                      onClick={handleNavClick}
                    >
                      <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-foreground" : "text-muted-foreground"}`} />
                      <div className="min-w-0">
                        <p className={`text-sm font-medium ${isActive ? "text-foreground" : "text-foreground"}`}>
                          {item.label}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">{item.desc}</p>
                      </div>
                    </NavLink>
                  );
                })}
              </nav>

              {/* Footer */}
              <div className="border-t border-border px-4 py-3">
                <p className="text-[10px] text-muted-foreground">RadarCuan v0.1</p>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
