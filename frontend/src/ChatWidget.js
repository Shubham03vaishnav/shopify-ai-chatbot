import { useState, useRef, useEffect } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { from: "bot", text: "👋 Hi! How can I help you today?" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages(prev => [...prev, { from: "user", text: userMsg }]);
    setInput("");
    setLoading(true);

    try {
      const res = await axios.post(`${API_URL}/chat`, { message: userMsg });
      setMessages(prev => [...prev, { from: "bot", text: res.data.reply }]);
    } catch {
      setMessages(prev => [...prev, { from: "bot", text: "Sorry, something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999, fontFamily: "sans-serif" }}>
      {open && (
        <div style={{
          width: 340, height: 480, background: "#fff",
          borderRadius: 16, boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
          display: "flex", flexDirection: "column", overflow: "hidden", marginBottom: 12
        }}>
          <div style={{ background: "#6366f1", color: "#fff", padding: "14px 16px", fontWeight: 700, fontSize: 15 }}>
            🛒 Store Assistant
            <span onClick={() => setOpen(false)} style={{ float: "right", cursor: "pointer", opacity: 0.8 }}>✕</span>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
            {messages.map((m, i) => (
              <div key={i} style={{
                alignSelf: m.from === "user" ? "flex-end" : "flex-start",
                background: m.from === "user" ? "#6366f1" : "#f3f4f6",
                color: m.from === "user" ? "#fff" : "#111",
                padding: "9px 13px", borderRadius: 12, maxWidth: "80%",
                fontSize: 13, lineHeight: 1.5, whiteSpace: "pre-wrap"
              }}>{m.text}</div>
            ))}
            {loading && (
              <div style={{ alignSelf: "flex-start", background: "#f3f4f6", padding: "9px 13px", borderRadius: 12, fontSize: 13, color: "#888" }}>
                Typing...
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div style={{ display: "flex", borderTop: "1px solid #e5e7eb", padding: 10, gap: 8 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendMessage()}
              placeholder="Ask about products..."
              style={{
                flex: 1, border: "1px solid #d1d5db", borderRadius: 8,
                padding: "8px 12px", fontSize: 13, outline: "none"
              }}
            />
            <button onClick={sendMessage} disabled={loading} style={{
              background: "#6366f1", color: "#fff", border: "none",
              borderRadius: 8, padding: "8px 14px", cursor: "pointer", fontWeight: 700
            }}>Send</button>
          </div>
        </div>
      )}

      <button onClick={() => setOpen(o => !o)} style={{
        width: 56, height: 56, borderRadius: "50%", background: "#6366f1",
        border: "none", color: "#fff", fontSize: 24, cursor: "pointer",
        boxShadow: "0 4px 16px rgba(99,102,241,0.5)", display: "block", marginLeft: "auto"
      }}>
        {open ? "✕" : "💬"}
      </button>
    </div>
  );
}