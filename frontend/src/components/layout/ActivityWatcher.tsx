import { useActivityWatcher } from "@/hooks/useActivityWatcher";

/** Headless component: keeps notification feed warm */
export function ActivityWatcher() {
  useActivityWatcher(true);
  return null;
}
