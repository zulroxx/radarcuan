import { useState } from "react";
import {
  GlobeHemisphereWest,
  List,
  LockKey,
  MagnifyingGlass,
  Sparkle,
  X,
} from "@phosphor-icons/react";
import { NavLink, useLocation } from "react-router-dom";
import FeedbackDialog from "@/components/FeedbackDialog";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { SCREENER } from "@/constants/testIds";

const linkClass = ({ isActive }) =>
  `flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
    isActive ? "bg-emerald-100 text-emerald-800" : "text-slate-500 hover:bg-slate-100"
  }`;

const navItems = [
  { to: "/", icon: MagnifyingGlass, label: "Screener", desc: "Screen saham IHSG" },
  { to: "/prediction", icon: Sparkle, label: "Agent Prediksi", desc: "Prediksi sektor & rekomendasi" },
  { to: "/macro", icon: GlobeHemisphereWest, label: "Makro Ekonomi", desc: "Indikator ekonomi makro" },
  { to: "/admin", icon: LockKey, label: "Admin", desc: "Panel admin" },
];

export default function AppHeader() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const { pathname } = useLocation();

  function handleNavClick() {
    setSheetOpen(false);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl" data-testid={SCREENER.header}>
      <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-2 px-4 py-3 sm:gap-4 sm:px-6 sm:py-4 lg:px-8">
        {/* Brand */}
        <div className="flex shrink-0 items-center gap-4 sm:gap-6">
          <div className="min-w-0 space-y-0.5">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              <Sparkle className="h-3 w-3 text-emerald-500" weight="fill" />
              <span className="hidden sm:inline">Public Beta Access</span>
              <span className="sm:hidden">Beta</span>
            </div>
            <h1 className="truncate text-lg font-bold tracking-tight text-slate-950 sm:text-xl lg:text-2xl" data-testid={SCREENER.heroTitle}>
              IHSG Smart Screener
            </h1>
          </div>

          {/* Desktop nav */}
          <nav className="hidden md:flex md:gap-1">
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
          {/* Mobile hamburger */}
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button className="md:hidden" size="icon" variant="ghost">
                <List className="h-5 w-5" />
                <span className="sr-only">Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent className="flex w-72 flex-col gap-0 p-0 [&>button.absolute]:hidden" side="left">
              <SheetTitle className="sr-only">Navigasi</SheetTitle>

              {/* Header sidebar */}
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                <div className="flex items-center gap-2">
                  <Sparkle className="h-4 w-4 text-emerald-500" weight="fill" />
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Menu
                  </span>
                </div>
                <SheetTrigger asChild>
                  <Button className="-mr-1 h-7 w-7" size="icon" variant="ghost">
                    <X className="h-4 w-4" />
                    <span className="sr-only">Tutup</span>
                  </Button>
                </SheetTrigger>
              </div>

              {/* Nav items */}
              <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.to;
                  return (
                    <NavLink
                      key={item.to}
                      className={`flex items-center gap-3 rounded-lg px-3 py-3 transition-colors ${
                        isActive
                          ? "bg-emerald-100 text-emerald-800"
                          : "text-slate-600 hover:bg-slate-100"
                      }`}
                      to={item.to}
                      onClick={handleNavClick}
                    >
                      <Icon className={`h-5 w-5 shrink-0 ${isActive ? "text-emerald-600" : "text-slate-400"}`} />
                      <div className="min-w-0">
                        <p className={`text-sm font-semibold ${isActive ? "text-emerald-800" : "text-slate-700"}`}>
                          {item.label}
                        </p>
                        <p className="truncate text-xs text-slate-400">{item.desc}</p>
                      </div>
                    </NavLink>
                  );
                })}
              </nav>

              {/* Footer */}
              <div className="border-t border-slate-200 px-5 py-4">
                <p className="text-[10px] text-slate-400">
                  IHSG Smart Screener v0.1
                </p>
              </div>
            </SheetContent>
          </Sheet>

          <FeedbackDialog />
        </div>
      </div>
    </header>
  );
}
