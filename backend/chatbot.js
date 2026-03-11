(function () {
  if (document.getElementById("ai-chatbot-iframe")) return;

  const iframe = document.createElement("iframe");
  iframe.id = "ai-chatbot-iframe";
  iframe.src = "https://shopify-ai-chatbot-three.vercel.app";
  iframe.setAttribute("allowtransparency", "true");
  iframe.setAttribute("scrolling", "no");
  iframe.style.cssText = "position:fixed;bottom:0;right:0;width:380px;height:100vh;border:none;z-index:999999;background:transparent;pointer-events:none";

  document.body.appendChild(iframe);

  window.addEventListener("message", function(e) {
    if (e.data === "chatbot-open") {
      iframe.style.pointerEvents = "all";
    }
    if (e.data === "chatbot-closed") {
      iframe.style.pointerEvents = "none";
    }
  });
})();