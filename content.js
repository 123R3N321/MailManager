(function () {
  "use strict";

  const BTN_ID = "ai-reply-gen-btn";
  const MODAL_ID = "ai-reply-modal";
  let cachedEmailContext = null;
  let debounceTimer = null;

  // ── Gmail DOM extraction ──────────────────────────────────────────────────

  function extractEmailContext() {
    const main = document.querySelector('div[role="main"]');
    if (!main) return null;

    // Subject
    const subjectEl =
      main.querySelector("h2[data-legacy-thread-id]") || main.querySelector("h2");
    const subject = subjectEl ? subjectEl.textContent.trim() : "(no subject)";

    // Find all message containers (thread)
    const messages = Array.from(main.querySelectorAll("div[data-message-id]"));
    if (messages.length === 0) return null;

    const latest = messages[messages.length - 1];

    // Sender
    const senderEl = latest.querySelector("span[email]");
    const senderName = senderEl ? senderEl.textContent.trim() : "Unknown";
    const senderEmail = senderEl ? senderEl.getAttribute("email") : "";

    // Body — prefer .a3s (Gmail's stable body class), fall back to dir=ltr div
    const bodyEl =
      latest.querySelector(".a3s") ||
      latest.querySelector("div[dir='ltr']") ||
      latest.querySelector("div[dir='auto']");
    if (!bodyEl) return null;

    const bodyText = stripHtml(bodyEl.innerHTML);
    if (!bodyText) return null;

    // Thread history (all messages except the latest)
    const threadHistory = messages
      .slice(0, -1)
      .map((msg) => {
        const el =
          msg.querySelector(".a3s") ||
          msg.querySelector("div[dir='ltr']") ||
          msg.querySelector("div[dir='auto']");
        return el ? stripHtml(el.innerHTML) : null;
      })
      .filter(Boolean);

    return { subject, senderName, senderEmail, bodyText, threadHistory };
  }

  function stripHtml(html) {
    return html
      .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "")
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/\s{2,}/g, " ")
      .trim();
  }

  // ── Button injection ──────────────────────────────────────────────────────

  function injectButton() {
    if (document.getElementById(BTN_ID)) return;

    const main = document.querySelector('div[role="main"]');
    if (!main || !main.querySelector("div[data-message-id]")) return;

    cachedEmailContext = extractEmailContext();

    const btn = document.createElement("button");
    btn.id = BTN_ID;
    btn.className = "ai-reply-btn";
    btn.textContent = "✨ Generate AI Reply";
    btn.title = cachedEmailContext ? "Generate a reply with AI" : "Could not read email content";
    if (!cachedEmailContext) btn.disabled = true;

    btn.addEventListener("click", handleGenerateClick);

    // Anchor near the reply button area — look for the toolbar row
    const toolbar =
      main.querySelector("div[gh='mtb']") || // Gmail's message toolbar
      main.querySelector("div[data-message-id]"); // fallback: attach to message container

    if (toolbar) {
      toolbar.parentNode.insertBefore(btn, toolbar.nextSibling);
    } else {
      main.prepend(btn);
    }
  }

  // ── Generate flow ─────────────────────────────────────────────────────────

  async function handleGenerateClick() {
    if (!cachedEmailContext) return;

    const btn = document.getElementById(BTN_ID);
    btn.disabled = true;
    btn.textContent = "⏳ Generating…";

    try {
      const response = await chrome.runtime.sendMessage({
        type: "GENERATE_REPLY",
        payload: cachedEmailContext,
      });

      if (response.success) {
        showModal(response.data.replyText, response.data.modelUsed);
      } else {
        showModal(null, null, response.error.message);
      }
    } catch (err) {
      const msg = err.message.includes("Extension context invalidated")
        ? "Extension was reloaded — please refresh this Gmail tab and try again."
        : "Extension error: " + err.message;
      showModal(null, null, msg);
    } finally {
      btn.disabled = false;
      btn.textContent = "✨ Generate AI Reply";
    }
  }

  // ── Modal ─────────────────────────────────────────────────────────────────

  function showModal(replyText, modelUsed, errorMessage) {
    removeModal();

    const overlay = document.createElement("div");
    overlay.id = MODAL_ID;
    overlay.className = "ai-reply-overlay";
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) removeModal();
    });

    const box = document.createElement("div");
    box.className = "ai-reply-box";

    const header = document.createElement("div");
    header.className = "ai-reply-header";
    header.innerHTML = `<strong>AI Reply</strong>${modelUsed ? `<span class="ai-reply-model">${modelUsed}</span>` : ""}`;

    const closeBtn = document.createElement("button");
    closeBtn.className = "ai-reply-close";
    closeBtn.textContent = "✕";
    closeBtn.addEventListener("click", removeModal);
    header.appendChild(closeBtn);

    const body = document.createElement("div");
    body.className = "ai-reply-body";

    if (errorMessage) {
      body.innerHTML = `<p class="ai-reply-error">⚠ ${errorMessage}</p>`;
    } else {
      const textarea = document.createElement("textarea");
      textarea.className = "ai-reply-textarea";
      textarea.value = replyText;
      textarea.rows = 10;
      body.appendChild(textarea);

      const copyBtn = document.createElement("button");
      copyBtn.className = "ai-reply-copy-btn";
      copyBtn.textContent = "Copy to clipboard";
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(textarea.value).then(() => {
          copyBtn.textContent = "Copied!";
          setTimeout(() => (copyBtn.textContent = "Copy to clipboard"), 1500);
        });
      });
      body.appendChild(copyBtn);
    }

    box.appendChild(header);
    box.appendChild(body);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
  }

  function removeModal() {
    const el = document.getElementById(MODAL_ID);
    if (el) el.remove();
  }

  // ── SPA navigation observer ───────────────────────────────────────────────

  function onDomMutation() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const main = document.querySelector('div[role="main"]');
      if (!main) return;

      const hasEmail = main.querySelector("div[data-message-id]");
      const btnExists = document.getElementById(BTN_ID);

      if (hasEmail && !btnExists) {
        injectButton();
      } else if (!hasEmail && btnExists) {
        document.getElementById(BTN_ID)?.remove();
        cachedEmailContext = null;
      }
    }, 300);
  }

  const observer = new MutationObserver(onDomMutation);
  observer.observe(document.body, { childList: true, subtree: true });

  // Run once on initial load in case Gmail opened directly to an email
  injectButton();
})();
