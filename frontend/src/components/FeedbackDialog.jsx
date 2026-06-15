import { useCallback, useState } from "react";
import { ChatCircleDots } from "@phosphor-icons/react";
import axios from "axios";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
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
        <Button className="shrink-0 rounded-full border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 hover:text-slate-900 sm:px-4 sm:text-sm" data-testid="header-feedback-button" type="button" variant="outline">
          <ChatCircleDots className="h-3.5 w-3.5 sm:h-4 sm:w-4" weight="duotone" />
          <span className="hidden sm:inline">Feedback</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="border-slate-200 bg-white sm:max-w-xl" data-testid="feedback-dialog">
        <DialogHeader className="text-left">
          <DialogTitle className="text-2xl text-slate-950">Bagikan feedback beta Anda</DialogTitle>
          <DialogDescription className="text-sm leading-6 text-slate-500">
            Masukan Anda membantu kami memprioritaskan fitur fundamental, watchlist, dan analisis premium berikutnya.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700" data-testid="feedback-name-label">Nama</label>
              <Input data-testid="feedback-name-input" name="name" onChange={handleChange} placeholder="Opsional" value={form.name} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700" data-testid="feedback-email-label">Email</label>
              <Input data-testid="feedback-email-input" name="email" onChange={handleChange} placeholder="opsional@email.com" type="email" value={form.email} />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700" data-testid="feedback-message-label">Feedback</label>
            <Textarea className="min-h-[150px]" data-testid="feedback-message-input" name="message" onChange={handleChange} placeholder="Contoh: tambahkan filter margin of safety, cash flow, atau screening sektoral..." value={form.message} />
          </div>
          <Button className="w-full rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400" data-testid="feedback-submit-button" disabled={loading} type="submit">
            {loading ? "Menyimpan feedback..." : "Kirim Feedback"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
