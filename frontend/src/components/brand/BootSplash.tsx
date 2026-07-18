/* Brief brand splash on first paint — respects reduced-motion */

import { useEffect, useState } from "react";
import { BrandLogo, BRAND } from "./BrandLogo";

const KEY = "afi_boot_seen_v1";

export function BootSplash() {
  const [visible, setVisible] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    try {
      if (sessionStorage.getItem(KEY)) return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        sessionStorage.setItem(KEY, "1");
        return;
      }
    } catch {
      return;
    }
    setVisible(true);
    const t1 = window.setTimeout(() => setDone(true), 900);
    const t2 = window.setTimeout(() => {
      setVisible(false);
      try {
        sessionStorage.setItem(KEY, "1");
      } catch {
        /* ignore */
      }
    }, 1250);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, []);

  if (!visible) return null;

  return (
    <div className={`afi-boot-screen ${done ? "is-done" : ""}`} aria-hidden>
      <div className="afi-boot-screen__inner">
        <BrandLogo variant="mark" size={72} animated colorScheme="dark" />
        <div className="afi-boot-screen__label">{BRAND.shortName}</div>
      </div>
    </div>
  );
}
