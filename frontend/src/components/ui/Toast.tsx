import { Toaster } from "sonner";

export const ToastProvider: React.FC = () => (
  <Toaster
    position="top-right"
    richColors
    closeButton
    duration={4000}
  />
);
