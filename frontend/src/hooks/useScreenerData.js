import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { toast } from "@/components/ui/sonner";

const initialWaitlistForm = {
  email: "",
  note: "",
};

export default function useScreenerData(apiBaseUrl) {
  const [waitlistLoading, setWaitlistLoading] = useState(false);
  const [waitlistForm, setWaitlistForm] = useState(initialWaitlistForm);
  const waitlistFormRef = useRef(waitlistForm);

  useEffect(() => {
    waitlistFormRef.current = waitlistForm;
  }, [waitlistForm]);

  const handleWaitlistChange = useCallback((event) => {
    const { name, value } = event.target;
    setWaitlistForm((current) => ({ ...current, [name]: value }));
  }, []);

  const submitWaitlist = useCallback(async (event) => {
    event.preventDefault();
    const { email, note } = waitlistFormRef.current;
    if (!email.trim()) {
      toast.error("Email waitlist wajib diisi.");
      return;
    }
    setWaitlistLoading(true);
    try {
      const response = await axios.post(`${apiBaseUrl}/waitlist`, {
        email,
        note: note || null,
      });
      if (response.data?.status === "updated") {
        toast.success("Minat premium Anda berhasil diperbarui.");
      } else {
        toast.success("Anda berhasil masuk waitlist premium.");
      }
      setWaitlistForm(initialWaitlistForm);
    } catch (error) {
      const msg = error.response?.data?.detail || "Gagal menyimpan waitlist.";
      toast.error(msg);
    } finally {
      setWaitlistLoading(false);
    }
  }, [apiBaseUrl]);

  return {
    waitlistLoading,
    waitlistForm,
    handleWaitlistChange,
    submitWaitlist,
  };
}

// Hook to fetch screener companies from TradingView API
export function useTradingViewScreener(apiBaseUrl) {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);

  const fetchCompanies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${apiBaseUrl}/screener/companies`);
      if (response.data.success) {
        setCompanies(response.data.data);
        setUpdatedAt(response.data.updated_at);
        if (response.data.from_cache) {
          toast.info(`Data screener dari cache: ${response.data.total} saham`);
        }
      } else {
        setError(response.data.message || "Gagal mengambil data");
        toast.error(response.data.message || "Gagal mengambil data");
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || "Terjadi kesalahan jaringan";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  return {
    companies,
    loading,
    error,
    updatedAt,
    refetch: fetchCompanies,
  };
}
