import { useState, useRef, useEffect } from "react";
import { Bot, X, Send, Sparkles } from "lucide-react";
import { sendChatMessage } from "../api";
import "./ChatWidget.css";

const WELCOME = {
  role: "assistant",
  content:
    "Hi! I'm the CivicTwin Assistant, connected live to the GIS map data. Ask me things like " +
    '"is there anything reported from Sector 62 to Sector 18" or "any critical waterlogging near Sector 78?"',
};

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending, open]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    const nextMessages = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setInput("");
    setSending(true);
    try {
      // Send full history minus the welcome placeholder so the model has
      // real multi-turn context (the welcome message was never something
      // the model said, so we drop it rather than confuse the transcript).
      const history = nextMessages.filter((m) => m !== WELCOME);
      const res = await sendChatMessage(history);
      setMessages((m) => [...m, { role: "assistant", content: res.reply, error: res.error }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Backend is offline. Make sure uvicorn is running on port 8000.", error: true },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <>
      {open && (
        <div className="chatwidget__panel">
          <div className="chatwidget__header">
            <div className="chatwidget__avatar">
              <Bot size={16} />
            </div>
            <div className="chatwidget__header-text">
              <div className="chatwidget__title">CivicTwin Assistant</div>
              <div className="chatwidget__subtitle">
                <Sparkles size={11} /> Route defect checker
              </div>
            </div>
            <button className="chatwidget__close" onClick={() => setOpen(false)} aria-label="Close chat">
              <X size={16} />
            </button>
          </div>

          <div className="chatwidget__messages" ref={scrollRef}>
            {messages.map((m, i) => (
              <div key={i} className={`chatwidget__bubble-row chatwidget__bubble-row--${m.role === "user" ? "user" : "bot"}`}>
                <div
                  className={`chatwidget__bubble chatwidget__bubble--${m.role === "user" ? "user" : "bot"} ${
                    m.error ? "chatwidget__bubble--error" : ""
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {sending && (
              <div className="chatwidget__bubble-row chatwidget__bubble-row--bot">
                <div className="chatwidget__bubble chatwidget__bubble--bot chatwidget__bubble--typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
          </div>

          <div className="chatwidget__input-row">
            <input
              type="text"
              placeholder="e.g. from Sector 62 to Sector 18"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button onClick={handleSend} disabled={sending || !input.trim()} aria-label="Send">
              <Send size={15} />
            </button>
          </div>
        </div>
      )}

      <button className="chatwidget__fab" onClick={() => setOpen((v) => !v)} aria-label="Open chat">
        {open ? <X size={22} /> : <Bot size={22} />}
      </button>
    </>
  );
}
