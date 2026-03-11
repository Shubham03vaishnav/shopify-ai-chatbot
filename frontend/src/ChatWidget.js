import { useState, useRef, useEffect } from "react";
import axios from "axios";

const API_URL = "https://shopify-ai-chatbot-production-0c5c.up.railway.app";

function ProductCard({ product }) {
  return (
    <div style={{
      background: "#fff", borderRadius: 12, overflow: "hidden",
      boxShadow: "0 2px 8px rgba(0,0,0,0.1)", marginBottom: 8, width: "100%"
    }}>
      {product.image && (
        <img
          src={product.image}
          alt={product.title}
          style={{ width: "100%", height: 140, objectFit: "cover" }}
        />
      )}
      <div style={{ padding: "10px 12px" }}>
        <div style={{ fontWeight: 700, fontSize: 13, color: "#1e293b", marginBottom: 4 }}>
          {product.title}
        </div>
        <div style={{ fontSize: 13, color: "#6366f1", fontWeight: 700, marginBottom: 8 }}>
          ₹{product.price}
        </div>
        
          href={product.url}
          target="_blank"
          rel="noreferrer"
          style={{
            display: "block", textAlign: "center",
            background: "#6366f1", color: "#fff",
            padding: "7px 0", borderRadius: 8,
            fontSize: 12, fontWeight: 700, textDecoration: "none"
          }}
        <a>
          Buy Now →
        </a>
      </div>
    </div>
  );
}

function OrderStatus({ order }) {
  const statusColor = {
    fulfilled: "#10b981",
    unfulfilled: "#f59e0b",
    cancelled: "#ef4444"
  };
  return (
    <div style={{
      background: "#fff", borderRadius: 12, padding: "12px 14px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.1)", marginBottom: 8
    }}>
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6 }}>
        Order #{order.number}
      </div>
      <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>
        📦 Status: <span style={{
          color: statusColor[order.status] || "#6366f1",
          fontWeight: 700, textTransform: "capitalize"
        }}>{order.status}</span>
      </div>
      <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>
        💰 Total: ₹{order.total}
      </div>
      <div style={{ fontSize: 12, color: "#64748b" }}>
        📅 Date: {order.date}
      </div>
    </div>
  );
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { from: "bot", text: "👋 Hi! How can I help you today?" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [waitingEmail, setWaitingEmail] = useState(false);
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
      const res = await axios.post(`${API_URL}/chat`, {
        message: userMsg,
        waiting_email: waitingEmail
      });

      if (res.data.type === "products") {
        setMessages(prev => [...prev, {
          from: "bot",
          text: res.data.reply,
          type: "products",
          products: res.data.products
        }]);
      } else if (res.data.type === "order") {
        setMessages(prev => [...prev, {
          from: "bot",
          text: res.data.reply,
          type: "order",
          order: res.data.order
        }]);
      } else if (res.data.type === "ask_email") {
        setWaitingEmail(true);
        setMessages(prev => [...prev, { from: "bot", text: res.data.reply }]);
      } else {
        setWaitingEmail(false);
        setMessages(prev => [...prev, { from: "bot", text: res.data.reply }]);
      }
    } catch {
      setMessages(prev => [...prev, {
        from: "bot", text: "Sorry, something went wrong. Please try again."
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999, fontFamily: "sans-serif" }}>
      {open && (
        <div style={{
          width: 340, height: 520, background: "#f8fafc",
          borderRadius: 16, boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
          display: "flex", flexDirection: "column", overflow: "hidden", marginBottom: 12
        }}>
          {/* Header */}
          <div style={{
            background: "#6366f1", color: "#fff",
            padding: "14px 16px", fontWeight: 700, fontSize: 15
          }}>
            🛒 Store Assistant
            <span onClick={() => setOpen(false)} style={{
              float: "right", cursor: "pointer", opacity: 0.8
            }}>✕</span>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: "auto", padding: 14,
            display: "flex", flexDirection: "column", gap: 10
          }}>
            {messages.map((m, i) => (
              <div key={i}>
                {m.type === "products" ? (
                  <div>
                    <div style={{
                      background: "#f3f4f6", padding: "9px 13px",
                      borderRadius: 12, fontSize: 13, marginBottom: 8
                    }}>{m.text}</div>
                    {m.products.map((p, j) => <ProductCard key={j} product={p} />)}
                  </div>
                ) : m.type === "order" ? (
                  <div>
                    <div style={{
                      background: "#f3f4f6", padding: "9px 13px",
                      borderRadius: 12, fontSize: 13, marginBottom: 8
                    }}>{m.text}</div>
                    <OrderStatus order={m.order} />
                  </div>
                ) : (
                  <div style={{
                    alignSelf: m.from === "user" ? "flex-end" : "flex-start",
                    background: m.from === "user" ? "#6366f1" : "#f3f4f6",
                    color: m.from === "user" ? "#fff" : "#111",
                    padding: "9px 13px", borderRadius: 12,
                    maxWidth: "80%", fontSize: 13,
                    lineHeight: 1.5, whiteSpace: "pre-wrap",
                    marginLeft: m.from === "user" ? "auto" : "0"
                  }}>{m.text}</div>
                )}
              </div>
            ))}
            {loading && (
              <div style={{
                background: "#f3f4f6", padding: "9px 13px",
                borderRadius: 12, fontSize: 13, color: "#888", width: "fit-content"
              }}>Typing...</div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div style={{
            display: "flex", borderTop: "1px solid #e5e7eb",
            padding: 10, gap: 8, background: "#fff"
          }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendMessage()}
              placeholder={waitingEmail ? "Enter your email..." : "Ask about products..."}
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