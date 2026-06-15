import { useEffect, useRef, useState } from "react";
import useDeferredVisibility from "@/hooks/useDeferredVisibility";

export default function DeferredChart({ active, className, testId, children }) {
  const ready = useDeferredVisibility(active);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!active || !containerRef.current) {
      setDimensions({ width: 0, height: 0 });
      return undefined;
    }

    const element = containerRef.current;
    const updateSizeState = () => {
      const { width, height } = element.getBoundingClientRect();
      setDimensions({ width: Math.floor(width), height: Math.floor(height) });
    };

    updateSizeState();

    const observer = new ResizeObserver(() => {
      updateSizeState();
    });

    observer.observe(element);
    return () => observer.disconnect();
  }, [active]);

  const hasMeasurableSize = dimensions.width > 0 && dimensions.height > 0;

  return (
    <div className={className} data-testid={testId} ref={containerRef}>
      {ready && hasMeasurableSize ? children(dimensions) : null}
    </div>
  );
}