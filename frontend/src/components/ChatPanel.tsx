import { useState, useCallback, useRef, useEffect, KeyboardEvent, Dispatch, SetStateAction } from "react";
import type { ChatMessage } from "@/types/api";
import { api } from "@/lib/api";
import { X, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";

interface Props {
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  onClose: () => void;
  onNewReply: () => void;
}

export default function ChatPanel({ messages, setMessages, onClose, onNewReply }: Props) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    const userMsg: ChatMessage = { role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setLoading(true);
    try {
      const res = await api.chat({ message: text, history: [...messages, userMsg] });
      setMessages((m) => [...m, { role: "assistant", text: res.reply }]);
      onNewReply();
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${e instanceof Error ? e.message : "Failed"}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, onNewReply]);

  const handleKey = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    },
    [send]
  );

  return (
    <div className="fixed bottom-20 right-5 z-50 w-[360px] max-w-[calc(100vw-2.5rem)] h-[480px] max-h-[calc(100vh-7rem)] bg-card border border-border rounded-lg shadow-xl flex flex-col animate-slide-up sm:bottom-20 sm:right-5 max-sm:inset-x-0 max-sm:bottom-0 max-sm:right-0 max-sm:w-full max-sm:h-[60vh] max-sm:rounded-b-none max-sm:rounded-t-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-semibold text-foreground">Chat Assistant</span>
        <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7">
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground text-center mt-8">Ask anything about cosmetic formulation.</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"}`}>
              {msg.role === "assistant" ? (
                <div className="prose prose-sm max-w-none"><ReactMarkdown>{msg.text}</ReactMarkdown></div>
              ) : (
                <span className="whitespace-pre-wrap">{msg.text}</span>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-lg px-3 py-2"><Loader2 className="h-4 w-4 animate-spin text-muted-foreground" /></div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border p-3 shrink-0">
        <div className="flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type a message…"
            rows={1}
            className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          <Button size="icon" onClick={send} disabled={!input.trim() || loading} className="shrink-0">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
