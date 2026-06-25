import { useEffect, useState } from "react";

export default function useDeferredVisibility(active, delay = 180) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!active) {
      setReady(false);
      return undefined;
    }

    const timeoutId = window.setTimeout(() => setReady(true), delay);
    return () => window.clearTimeout(timeoutId);
  }, [active, delay, setReady]);

  return ready;
}