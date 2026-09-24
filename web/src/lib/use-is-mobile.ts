"use client";

import { useEffect, useState } from "react";

// True when the viewport is phone-width (< 768px). Used to switch inline-styled
// grids to stacked layouts on mobile (the codebase styles inline, so media
// queries can't be used directly).
export function useIsMobile(breakpoint = 768): boolean {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    const update = () => setMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, [breakpoint]);
  return mobile;
}
