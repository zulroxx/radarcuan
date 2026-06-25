import { useCallback, useState } from "react";
import { ChatCircleDots } from "@phosphor-icons/react";
import axios from "axios";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

export default function FeedbackDialog() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const [loading, setLoading] = useState(false);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (form.message.trim().length < 5) {
      toast.error("Isi feedback minimal 5 karakter.");
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/feedback`, {
        name: form.name || null,
        email: form.email || null,
        message: form.message,
      });
      toast.success("Feedback berhasil disimpan.");
      setForm({ name: "", email: "", message: "" });
      setOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Gagal menyimpan feedback.");
    } finally {
      setLoading(false);
    }
  }, [form]);

  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <Button className="shrink-0 border border-border bg-card px-2.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground sm:px-3 sm:text-sm" data-testid="header-feedback-button" type="button" variant="outline">
          <ChatCircleDots className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          <span className="hidden sm:inline">Feedback</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="border-border bg-card sm:max-w-xl" data-testid="feedback-dialog">
        <DialogHeader className="text-left">
          <DialogTitle className="text-xl text-foreground">Bagikan feedback beta Anda</DialogTitle>
          <DialogDescription className="text-sm leading-6 text-muted-foreground">
            Masukan Anda membantu kami memprioritaskan fitur fundamental, watchlist, dan analisis premium berikutnya.
          </DialogDescription>
        </DialogHeader>
        <form autoComplete="on" className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground" data-testid="feedback-name-label">Nama</label>
              <Input data-testid="feedback-name-input" id="feedback-name" name="name" autoComplete="name" onChange={handleChange} placeholder="Opsional" value={form.name} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground" data-testid="feedback-email-label">Email</label>
              <Input data-testid="feedback-email-input" id="feedback-email" name="email" autoComplete="email" onChange={handleChange} placeholder="opsional@email.com" type="email" value={form.email} />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground" data-testid="feedback-message-label">Feedback</label>
            <Textarea className="min-h-[150px]" data-testid="feedback-message-input" id="feedback-message" name="message" onChange={handleChange} placeholder="Contoh: tambahkan filter margin of safety, cash flow, atau screening sektoral..." value={form.message} />
          </div>
          <Button className="w-full bg-foreground text-background hover:bg-foreground/90" data-testid="feedback-submit-button" disabled={loading} type="submit">
            {loading ? "Menyimpan feedback..." : "Kirim Feedback"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
