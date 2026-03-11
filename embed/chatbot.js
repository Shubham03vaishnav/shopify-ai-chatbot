(function () {
  if (document.getElementById("ai-chatbot-iframe")) return;

  const iframe = document.createElement("iframe");
  iframe.id = "ai-chatbot-iframe";
  iframe.src = "https://shopify-ai-chatbot-three.vercel.app";
  iframe.style.cssText = [
    "position:fixed",
    "bottom:20px",
    "right:20px",
    "width:380px",
    "height:520px",
    "border:none",
    "z-index:999999",
    "border-radius:16px",
    "box-shadow:0 8px 32px rgba(0,0,0,0.2)"
  ].join(";");

  document.body.appendChild(iframe);
})();