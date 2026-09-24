"use client";

import { useEffect, useRef } from "react";

// Reports the widget's rendered height to the host page via postMessage,
// so the embedding iframe can auto-resize.
export default function EmbedFrame() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const send = () => {
      const h = document.documentElement.scrollHeight;
      window.parent?.postMessage({ type: "ii-embed-height", height: h }, "*");
    };
    send();
    // Re-report when results render/unrender (content height changes).
    const obs = new ResizeObserver(send);
    obs.observe(document.body);
    return () => obs.disconnect();
  }, []);

  return <div ref={ref} aria-hidden="true" style={{ position: "absolute", width: 0, height: 0 }} />;
}
