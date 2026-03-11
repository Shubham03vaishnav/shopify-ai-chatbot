import { useState, useRef, useEffect } from "react";
import axios from "axios";

const API_URL = "https://shopify-ai-chatbot-production-0c5c.up.railway.app";

function ProductCard({ product }) {
  return (
    <div style={{background:"#fff",borderRadius:10,boxShadow:"0 1px 4px rgba(0,0,0,0.08)",marginBottom:6,padding:"10px 12px",border:"1px solid #f0f0f0"}}>
      <div style={{fontWeight:600,fontSize:12,color:"#1e293b",marginBottom:2}}>{product.title}</div>
      <div style={{fontSize:12,color:"#6366f1",fontWeight:700,marginBottom:8}}>Rs. {product.price}</div>
      <button onClick={() => window.open(product.url, "_blank")} style={{background:"#f0f0ff",color:"#6366f1",padding:"5px 12px",borderRadius:6,fontSize:11,fontWeight:600,border:"1px solid #6366f1",cursor:"pointer"}}>View Product</button>
    </div>
  );
}

function OrderStatus({ order }) {
  const statusColor = {fulfilled:"#10b981",unfulfilled:"#f59e0b",cancelled:"#ef4444"};
  return (
    <div style={{background:"#fff",borderRadius:10,padding:"12px 14px",boxShadow:"0 1px 4px rgba(0,0,0,0.08)",marginBottom:6,border:"1px solid #f0f0f0"}}>
      <div style={{fontWeight:700,fontSize:12,marginBottom:6}}>Order #{order.number}</div>
      <div style={{fontSize:12,color:"#64748b",marginBottom:3}}>Status: <span style={{color:statusColor[order.status]||"#6366f1",fontWeight:700,textTransform:"capitalize"}}>{order.status}</span></div>
      <div style={{fontSize:12,color:"#64748b",marginBottom:3}}>Total: Rs. {order.total}</div>
      <div style={{fontSize:12,color:"#64748b"}}>Date: {order.date}</div>
    </div>
  );
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{from:"bot",text:"Hi! How can I help you today?"}]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [waitingEmail, setWaitingEmail] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({behavior:"smooth"});
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages(prev => [...prev, {from:"user",text:userMsg}]);
    setInput("");
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/chat`, {message:userMsg, waiting_email:waitingEmail});
      if (res.data.type === "products") {
        setMessages(prev => [...prev, {from:"bot",text:res.data.reply,type:"products",products:res.data.products}]);
      } else if (res.data.type === "order") {
        setMessages(prev => [...prev, {from:"bot",text:res.data.reply,type:"order",order:res.data.order}]);
      } else if (res.data.type === "ask_email") {
        setWaitingEmail(true);
        setMessages(prev => [...prev, {from:"bot",text:res.data.reply}]);
      } else {
        setWaitingEmail(false);
        setMessages(prev => [...prev, {from:"bot",text:res.data.reply}]);
      }
    } catch {
      setMessages(prev => [...prev, {from:"bot",text:"Sorry, something went wrong. Please try again."}]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{position:"fixed",bottom:20,right:20,zIndex:9999,fontFamily:"sans-serif"}}>
      {open && (
        <div style={{width:300,height:460,background:"#f8fafc",borderRadius:14,boxShadow:"0 4px 24px rgba(0,0,0,0.12)",display:"flex",flexDirection:"column",overflow:"hidden",marginBottom:10,border:"1px solid #e2e8f0"}}>
          <div style={{background:"#6366f1",color:"#fff",padding:"12px 14px",fontWeight:700,fontSize:13,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span>Store Assistant</span>
            <span onClick={() => setOpen(false)} style={{cursor:"pointer",opacity:0.8,fontSize:16}}>X</span>
          </div>
          <div style={{flex:1,overflowY:"auto",padding:12,display:"flex",flexDirection:"column",gap:8}}>
            {messages.map((m, i) => (
              <div key={i}>
                {m.type === "products" ? (
                  <div>
                    <div style={{background:"#f3f4f6",padding:"8px 11px",borderRadius:10,fontSize:12,marginBottom:6,color:"#475569"}}>{m.text}</div>
                    {m.products.map((p, j) => (
                      <ProductCard key={j} product={p} />
                    ))}
                  </div>
                ) : m.type === "order" ? (
                  <div>
                    <div style={{background:"#f3f4f6",padding:"8px 11px",borderRadius:10,fontSize:12,marginBottom:6}}>{m.text}</div>
                    <OrderStatus order={m.order} />
                  </div>
                ) : (
                  <div style={{alignSelf:m.from==="user"?"flex-end":"flex-start",background:m.from==="user"?"#6366f1":"#fff",color:m.from==="user"?"#fff":"#334155",padding:"8px 11px",borderRadius:10,maxWidth:"82%",fontSize:12,lineHeight:1.5,whiteSpace:"pre-wrap",marginLeft:m.from==="user"?"auto":"0",boxShadow:"0 1px 3px rgba(0,0,0,0.06)",border:m.from==="user"?"none":"1px solid #f0f0f0"}}>{m.text}</div>
                )}
              </div>
            ))}
            {loading && (
              <div style={{background:"#fff",padding:"8px 11px",borderRadius:10,fontSize:12,color:"#94a3b8",width:"fit-content",border:"1px solid #f0f0f0"}}>Typing...</div>
            )}
            <div ref={bottomRef} />
          </div>
          <div style={{display:"flex",borderTop:"1px solid #e2e8f0",padding:"8px 10px",gap:6,background:"#fff"}}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendMessage()}
              placeholder={waitingEmail ? "Enter your email..." : "Ask about products..."}
              style={{flex:1,border:"1px solid #e2e8f0",borderRadius:8,padding:"7px 10px",fontSize:12,outline:"none",color:"#334155"}}
            />
            <button onClick={sendMessage} disabled={loading} style={{background:"#6366f1",color:"#fff",border:"none",borderRadius:8,padding:"7px 12px",cursor:"pointer",fontWeight:600,fontSize:12}}>Send</button>
          </div>
        </div>
      )}
      <button onClick={() => setOpen(o => !o)} style={{width:50,height:50,borderRadius:"50%",background:"#6366f1",border:"none",color:"#fff",fontSize:22,cursor:"pointer",boxShadow:"0 4px 14px rgba(99,102,241,0.45)",display:"block",marginLeft:"auto"}}>
        {open ? "X" : "C"}
      </button>
    </div>
  );
}