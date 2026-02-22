/**
 * Global notification (ribbon) - slide from right, success/error/warning, auto-dismiss 5s, dismiss on X.
 * Use from any page via useNotification().
 */

import React, { createContext, useCallback, useContext, useState } from "react";
import { X } from "lucide-react";

export type NotificationType = "success" | "error" | "warning";

export interface NotificationOptions {
  type: NotificationType;
  message: string;
  /** Auto-dismiss after ms; default 5000. Set 0 to disable. */
  timeout?: number;
}

interface NotificationState extends NotificationOptions {
  id: number;
  visible: boolean;
}

interface NotificationContextValue {
  show: (options: NotificationOptions) => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

const DEFAULT_TIMEOUT = 5000;

const typeStyles: Record<
  NotificationType,
  { bg: string; border: string; text: string }
> = {
  success: {
    bg: "bg-emerald-500",
    border: "border-emerald-600",
    text: "text-white",
  },
  error: {
    bg: "bg-red-500",
    border: "border-red-600",
    text: "text-white",
  },
  warning: {
    bg: "bg-amber-500",
    border: "border-amber-600",
    text: "text-white",
  },
};

function NotificationRibbon({
  notif,
  onDismiss,
}: {
  notif: NotificationState;
  onDismiss: () => void;
}) {
  const [exiting, setExiting] = useState(false);
  const [entered, setEntered] = useState(false);
  const styles = typeStyles[notif.type];

  React.useEffect(() => {
    const t = requestAnimationFrame(() => {
      requestAnimationFrame(() => setEntered(true));
    });
    return () => cancelAnimationFrame(t);
  }, []);

  const handleDismiss = useCallback(() => {
    setExiting(true);
    setTimeout(onDismiss, 300);
  }, [onDismiss]);

  const translate = exiting ? "translate-x-[120%]" : entered ? "translate-x-0" : "translate-x-[120%]";

  return (
    <div
      role="alert"
      className={`
        fixed top-4 right-4 z-[100] flex min-w-[280px] max-w-md items-center gap-3 rounded-lg border-l-4 px-4 py-3 shadow-lg
        ${styles.bg} ${styles.border} ${styles.text}
        transition-transform duration-300 ease-out ${translate}
      `}
    >
      <p className="flex-1 text-sm font-medium">{notif.message}</p>
      <button
        type="button"
        onClick={handleDismiss}
        className="rounded p-1 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notification, setNotification] = useState<NotificationState | null>(null);
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const dismiss = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setNotification((prev) => (prev ? { ...prev, visible: false } : null));
  }, []);

  const show = useCallback(
    (options: NotificationOptions) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      const id = Date.now();
      const timeoutMs = options.timeout ?? DEFAULT_TIMEOUT;
      setNotification({
        id,
        ...options,
        visible: true,
      });
      if (timeoutMs > 0) {
        timeoutRef.current = setTimeout(() => {
          timeoutRef.current = null;
          setNotification((prev) => (prev?.id === id ? null : prev));
        }, timeoutMs);
      }
    },
    []
  );

  return (
    <NotificationContext.Provider value={{ show }}>
      {children}
      {notification?.visible && (
        <NotificationRibbon notif={notification} onDismiss={dismiss} />
      )}
    </NotificationContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useNotification(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error("useNotification must be used within NotificationProvider");
  }
  return ctx;
}
