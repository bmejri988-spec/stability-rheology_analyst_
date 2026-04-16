import { useState, useCallback, useRef, useEffect, lazy, Suspense } from "react";
import { MessageCircle } from "lucide-react";

const ChatPanel = lazy(() => import("./ChatPanel"));

export default function ChatLauncher() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);

  const handleNewReply = useCallback(() => {
    if (!open) setUnread((n) => n + 1);
  }, [open]);

  const toggle = useCallback(() => {
    setOpen((o) => !o);
    setUnread(0);
  }, []);

  return (
    <>
      <button
        onClick={toggle}
        aria-label="Open chat assistant"
        className="fixed bottom-5 right-5 z-50 h-12 w-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-lg hover:opacity-90 transition-opacity"
      >
        <MessageCircle className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <Suspense fallback={null}>
          <ChatPanel onClose={toggle} onNewReply={handleNewReply} />
        </Suspense>
      )}
    </>
  );
}
