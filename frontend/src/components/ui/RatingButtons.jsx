import { ThumbsDown, ThumbsUp } from "@phosphor-icons/react";
import axios from "axios";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

export default function RatingButtons({ agentType, targetId, sector, ticker, size = 14 }) {
  const handleRate = async (rating) => {
    try {
      await axios.post(`${API_BASE}/feedback/rating`, {
        agent_type: agentType,
        target_id: targetId,
        rating,
        sector: sector || null,
        ticker: ticker || null,
      });
      toast.success(rating === 1 ? "Feedback positif tersimpan" : "Feedback negatif tersimpan");
    } catch {
      toast.error("Gagal menyimpan feedback");
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => handleRate(1)}
        className="rounded p-0.5 text-muted-foreground transition-colors hover:text-cuan"
        title="Berguna"
      >
        <ThumbsUp size={size} />
      </button>
      <button
        onClick={() => handleRate(-1)}
        className="rounded p-0.5 text-muted-foreground transition-colors hover:text-loss"
        title="Tidak berguna"
      >
        <ThumbsDown size={size} />
      </button>
    </div>
  );
}
