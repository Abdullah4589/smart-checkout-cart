// Smart Checkout MVP — frontend
// Phase 1: camera control, catalog load, cart rendering scaffold.
// Detection + live billing are wired in later phases.

const els = {
  video: document.getElementById("video"),
  overlay: document.getElementById("overlay"),
  cameraMsg: document.getElementById("camera-msg"),
  btnCamera: document.getElementById("btn-camera"),
  btnSwitchCamera: document.getElementById("btn-switch-camera"),
  btnReset: document.getElementById("btn-reset"),
  detectedItem: document.getElementById("detected-item"),
  cartBody: document.getElementById("cart-body"),
  grandTotal: document.getElementById("grand-total"),
  itemCount: document.getElementById("item-count"),
  catalogList: document.getElementById("catalog-list"),
  statusDot: document.getElementById("status-dot"),
  statusText: document.getElementById("status-text"),
  banner: document.getElementById("banner"),
  chkDebug: document.getElementById("chk-debug"),
  btnCheckout: document.getElementById("btn-checkout"),
  receiptOverlay: document.getElementById("receipt-overlay"),
  receiptBody: document.getElementById("receipt-body"),
  receiptTotal: document.getElementById("receipt-total"),
  btnReceiptClose: document.getElementById("btn-receipt-close"),
  storeName: document.getElementById("store-name"),
  storeBranch: document.getElementById("store-branch"),
  subtotal: document.getElementById("subtotal"),
  gstLabel: document.getElementById("gst-label"),
  gstAmount: document.getElementById("gst-amount"),
  paymentOverlay: document.getElementById("payment-overlay"),
  paymentMethods: document.getElementById("payment-methods"),
  btnPaymentCancel: document.getElementById("btn-payment-cancel"),
  receiptStoreName: document.getElementById("receipt-store-name"),
  receiptStoreBranch: document.getElementById("receipt-store-branch"),
  receiptMeta: document.getElementById("receipt-meta"),
  receiptSubtotal: document.getElementById("receipt-subtotal"),
  receiptGstLabel: document.getElementById("receipt-gst-label"),
  receiptGst: document.getElementById("receipt-gst"),
  receiptPayment: document.getElementById("receipt-payment"),
};

let debugView = false;
let lastCartSummary = null;
let storeInfo = { name: "SmartCart", branch: "", currency_symbol: "Rs. ", gst_rate: 0.17, payment_methods: ["Cash"] };

let stream = null;
// Prefer the back/environment camera first (better for scanning items held up
// to the lens); toggled by the Switch Camera button on devices with 2+ cameras.
let facingMode = "environment";

// One session per checkout lane. Persisted so a refresh keeps the same cart.
let sessionId = localStorage.getItem("checkout_session");
if (!sessionId) {
  sessionId = "sess-" + Math.random().toString(36).slice(2, 10);
  localStorage.setItem("checkout_session", sessionId);
}

// Detection loop state
const DETECT_INTERVAL_MS = 700; // send a frame ~1.4x/sec (not every frame)
let detectTimer = null;
let detectInFlight = false;
const captureCanvas = document.createElement("canvas");

// ---------- status ----------
function setStatus(text, kind = "idle") {
  els.statusText.textContent = text;
  els.statusDot.className = "dot dot-" + kind;
}

// ---------- error banner ----------
function showBanner(text) {
  els.banner.textContent = text;
  els.banner.classList.remove("hidden");
}

function hideBanner() {
  els.banner.classList.add("hidden");
}

// ---------- camera ----------
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: facingMode },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
    els.video.srcObject = stream;
    els.cameraMsg.classList.add("hidden");
    els.btnCamera.textContent = "Stop Camera";
    setStatus("Camera live", "live");
    hideBanner();
    await new Promise((r) => {
      if (els.video.readyState >= 2) r();
      else els.video.onloadeddata = () => r();
    });
    startDetectionLoop();
    updateSwitchCameraVisibility();
  } catch (err) {
    console.error("Camera error:", err);
    const msg =
      err.name === "NotAllowedError"
        ? "Camera permission denied — allow camera access in your browser to continue the demo."
        : "No camera found — connect a webcam and click Start Camera again.";
    els.cameraMsg.textContent = msg;
    els.cameraMsg.classList.remove("hidden");
    setStatus("Camera error", "err");
    showBanner(msg);
  }
}

function stopCamera() {
  stopDetectionLoop();
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  els.video.srcObject = null;
  els.cameraMsg.textContent = "Camera off";
  els.cameraMsg.classList.remove("hidden");
  els.btnCamera.textContent = "Start Camera";
  els.detectedItem.textContent = "—";
  els.btnSwitchCamera.hidden = true;
  clearOverlay();
  setStatus("Idle", "idle");
}

// Only show the switch button when the device actually has 2+ cameras
// (enumerateDevices only returns labeled results once permission is granted,
// i.e. after the first getUserMedia call).
async function updateSwitchCameraVisibility() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter((d) => d.kind === "videoinput");
    els.btnSwitchCamera.hidden = cameras.length < 2;
  } catch (err) {
    console.error("enumerateDevices failed:", err);
  }
}

async function switchCamera() {
  if (!stream) return;
  facingMode = facingMode === "environment" ? "user" : "environment";
  stream.getTracks().forEach((t) => t.stop());
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: facingMode },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
    els.video.srcObject = stream;
    await new Promise((r) => {
      if (els.video.readyState >= 2) r();
      else els.video.onloadeddata = () => r();
    });
  } catch (err) {
    console.error("Switch camera failed:", err);
    showBanner("Could not switch camera — your device may only expose one.");
  }
}

els.btnSwitchCamera.addEventListener("click", switchCamera);

// ---------- detection loop ----------
function startDetectionLoop() {
  if (detectTimer) return;
  detectTimer = setInterval(captureAndDetect, DETECT_INTERVAL_MS);
}

function stopDetectionLoop() {
  if (detectTimer) clearInterval(detectTimer);
  detectTimer = null;
}

function clearOverlay() {
  const ctx = els.overlay.getContext("2d");
  ctx.clearRect(0, 0, els.overlay.width, els.overlay.height);
}

// Cap the long edge of the frame we upload — the model resizes internally
// anyway, so sending full 1280x720 just wastes upload time + CPU on a
// resource-constrained server. Smaller frame = faster round trip = the
// COUNT_CONFIRM_POLLS debounce (cart.py) resolves in real seconds instead of
// many, which is what actually made multi-item scans feel slow/missed.
const MAX_SEND_DIM = 640;

async function captureAndDetect() {
  if (detectInFlight || !stream) return;
  const vw = els.video.videoWidth;
  const vh = els.video.videoHeight;
  if (!vw || !vh) return;

  detectInFlight = true;
  try {
    const scale = Math.min(1, MAX_SEND_DIM / Math.max(vw, vh));
    const sendW = Math.round(vw * scale);
    const sendH = Math.round(vh * scale);
    captureCanvas.width = sendW;
    captureCanvas.height = sendH;
    captureCanvas.getContext("2d").drawImage(els.video, 0, 0, sendW, sendH);
    const blob = await new Promise((res) =>
      captureCanvas.toBlob(res, "image/jpeg", 0.7)
    );
    if (!blob) return;

    const form = new FormData();
    form.append("frame", blob, "frame.jpg");
    form.append("session", sessionId);
    const res = await fetch("/api/detect", { method: "POST", body: form });
    if (!res.ok) throw new Error(`server ${res.status}`);
    const data = await res.json();

    if (!data.model_loaded) {
      setStatus(
        data.model_error ? "Model failed to load" : "Loading model…",
        data.model_error ? "err" : "idle"
      );
      els.detectedItem.textContent = data.model_error
        ? "model error — see console"
        : "loading detector…";
      if (data.model_error) {
        showBanner("Detection model failed to load — scanning is unavailable until the server is fixed.");
      }
    } else {
      setStatus("Detecting", "live");
      hideBanner();
    }
    // Detection boxes are in the (possibly downscaled) sent-frame's pixel
    // space — scale back up to the video's native size for the overlay.
    const detections = data.detections || [];
    const backToVideo = 1 / scale;
    if (backToVideo !== 1) {
      for (const d of detections) {
        d.box = d.box.map((v) => Math.round(v * backToVideo));
      }
    }
    drawDetections(detections, vw, vh);
    updateDetectedBar(detections);
    if (data.cart) renderCart(data.cart);
  } catch (err) {
    console.error("Detect error:", err);
    setStatus("Backend unreachable", "err");
    showBanner("Lost connection to the server — detection is paused. It will resume automatically once the connection is back.");
  } finally {
    detectInFlight = false;
  }
}

function drawDetections(detections, vw, vh) {
  const c = els.overlay;
  c.width = vw;
  c.height = vh;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, vw, vh);
  ctx.lineWidth = Math.max(2, vw / 400);
  ctx.font = `${Math.max(14, vw / 55)}px "Segoe UI", sans-serif`;
  ctx.textBaseline = "top";

  for (const d of detections) {
    const [x1, y1, x2, y2] = d.box;
    // Matched catalog product -> green + product name; unknown object -> gray.
    const matched = d.matched;
    const color = matched ? "#33c58a" : "#7a8199";
    const name = matched ? d.product_name : d.label;
    const label = debugView ? `${name} ${(d.confidence * 100).toFixed(0)}%` : name;

    ctx.strokeStyle = color;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    const tw = ctx.measureText(label).width;
    const th = parseInt(ctx.font, 10) + 6;
    ctx.fillStyle = color;
    ctx.fillRect(x1, Math.max(0, y1 - th), tw + 10, th);
    ctx.fillStyle = "#0f1220";
    ctx.fillText(label, x1 + 5, Math.max(0, y1 - th) + 3);
  }
}

function updateDetectedBar(detections) {
  if (!detections.length) {
    els.detectedItem.textContent = "—";
    return;
  }
  // Summarize everything in frame as "N× Product" (matched) / "N× label?" (unknown).
  const counts = new Map();
  for (const d of detections) {
    const key = d.matched ? d.product_name : `${d.label}?`;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  els.detectedItem.textContent = [...counts.entries()]
    .map(([name, n]) => (n > 1 ? `${n}× ${name}` : name))
    .join(", ");
}

els.btnCamera.addEventListener("click", () => {
  if (stream) stopCamera();
  else startCamera();
});

els.chkDebug.addEventListener("change", () => {
  debugView = els.chkDebug.checked;
});

// ---------- cart rendering ----------
function money(n) {
  const amount = Math.round(n || 0).toLocaleString("en-PK");
  return storeInfo.currency_symbol + amount;
}

function renderCart(summary) {
  lastCartSummary = summary;
  const items = (summary && summary.items) || [];
  const totalQty = items.reduce((sum, it) => sum + it.qty, 0);
  els.itemCount.textContent = `${totalQty} item${totalQty === 1 ? "" : "s"}`;
  els.btnCheckout.disabled = totalQty === 0;

  els.subtotal.textContent = money((summary && summary.subtotal) || 0);
  els.gstAmount.textContent = money((summary && summary.gst_amount) || 0);
  els.gstLabel.textContent = `GST (${Math.round((storeInfo.gst_rate || 0) * 100)}%)`;

  els.cartBody.innerHTML = "";
  if (items.length === 0) {
    els.cartBody.innerHTML =
      '<tr class="empty-row"><td colspan="5">Cart is empty</td></tr>';
    els.grandTotal.textContent = money(0);
    return;
  }
  for (const item of items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="col-name">${item.name}</td>
      <td class="col-qty">
        <div class="qty-ctrl">
          <button class="qty-btn" data-act="dec" data-sku="${item.sku}" title="Decrease">−</button>
          <span class="qty-val">${item.qty}</span>
          <button class="qty-btn" data-act="inc" data-sku="${item.sku}" title="Increase">+</button>
        </div>
      </td>
      <td class="col-price">${money(item.unit_price)}</td>
      <td class="col-total">${money(item.line_total)}</td>
      <td class="col-actions">
        <button class="remove-btn" data-act="remove" data-sku="${item.sku}" title="Remove item">✕</button>
      </td>`;
    // Stash current qty for the +/- handlers.
    tr.querySelectorAll(".qty-btn").forEach((b) => (b.dataset.qty = item.qty));
    els.cartBody.appendChild(tr);
  }
  els.grandTotal.textContent = money(summary.grand_total);
}

// Delegated handler for manual overrides (rows re-render each detection poll).
els.cartBody.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-act]");
  if (!btn) return;
  const { act, sku } = btn.dataset;
  const qty = parseInt(btn.dataset.qty || "0", 10);
  try {
    let res;
    if (act === "remove") {
      res = await fetch(
        `/api/cart/remove?session=${encodeURIComponent(sessionId)}&sku=${encodeURIComponent(sku)}`,
        { method: "POST" }
      );
    } else {
      const newQty = act === "inc" ? qty + 1 : qty - 1;
      res = await fetch(
        `/api/cart/set-qty?session=${encodeURIComponent(sessionId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sku, qty: newQty }),
        }
      );
    }
    renderCart(await res.json());
  } catch (err) {
    console.error("Cart action failed:", err);
    setStatus("Cart update failed", "err");
  }
});

// ---------- reset ----------
els.btnReset.addEventListener("click", async () => {
  try {
    const res = await fetch(
      `/api/cart/reset?session=${encodeURIComponent(sessionId)}`,
      { method: "POST" }
    );
    renderCart(await res.json());
  } catch (err) {
    console.error("Reset failed:", err);
  }
});

// ---------- checkout / receipt ----------
els.btnCheckout.addEventListener("click", () => {
  if (!lastCartSummary || !lastCartSummary.items.length) return;
  openPaymentPicker();
});

function openPaymentPicker() {
  els.paymentMethods.innerHTML = (storeInfo.payment_methods || ["Cash"])
    .map((m) => `<button class="btn payment-btn" data-method="${m}">${paymentIcon(m)} ${m}</button>`)
    .join("");
  els.paymentOverlay.classList.remove("hidden");
}

function paymentIcon(method) {
  return { Cash: "💵", Card: "💳", JazzCash: "📱", EasyPaisa: "📲" }[method] || "💰";
}

els.paymentMethods.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-method]");
  if (!btn) return;
  els.paymentOverlay.classList.add("hidden");
  await completeCheckout(btn.dataset.method);
});

els.btnPaymentCancel.addEventListener("click", () => {
  els.paymentOverlay.classList.add("hidden");
});

async function completeCheckout(paymentMethod) {
  try {
    const res = await fetch(
      `/api/cart/checkout?session=${encodeURIComponent(sessionId)}&payment_method=${encodeURIComponent(paymentMethod)}`,
      { method: "POST" }
    );
    const receipt = await res.json();
    showReceipt(receipt);
    renderCart({ items: [], subtotal: 0, gst_amount: 0, grand_total: 0 });
  } catch (err) {
    console.error("Checkout failed:", err);
    showBanner("Checkout failed — could not reach the server. Try again.");
  }
}

function showReceipt(receipt) {
  const items = receipt.items || [];
  els.receiptStoreName.textContent = storeInfo.name;
  els.receiptStoreBranch.textContent = storeInfo.branch || "";
  const dt = receipt.completed_at
    ? new Date(receipt.completed_at * 1000).toLocaleString("en-PK")
    : new Date().toLocaleString("en-PK");
  els.receiptMeta.textContent = `${receipt.invoice_no || ""} · ${dt}`;
  els.receiptBody.innerHTML = items
    .map(
      (it) => `
      <div class="receipt-row">
        <span class="rname">${it.qty}× ${it.name}</span>
        <span class="rmeta">${money(it.line_total)}</span>
      </div>`
    )
    .join("");
  els.receiptSubtotal.textContent = money(receipt.subtotal || 0);
  els.receiptGstLabel.textContent = `GST (${Math.round((receipt.gst_rate ?? storeInfo.gst_rate ?? 0) * 100)}%)`;
  els.receiptGst.textContent = money(receipt.gst_amount || 0);
  els.receiptTotal.textContent = money(receipt.grand_total || 0);
  els.receiptPayment.textContent = `Paid via ${receipt.payment_method || "Cash"}`;
  els.receiptOverlay.classList.remove("hidden");
}

els.btnReceiptClose.addEventListener("click", () => {
  els.receiptOverlay.classList.add("hidden");
});

async function loadCart() {
  try {
    const res = await fetch(
      `/api/cart?session=${encodeURIComponent(sessionId)}`
    );
    renderCart(await res.json());
  } catch (err) {
    console.error("Cart load failed:", err);
    renderCart(null);
  }
}

// ---------- catalog ----------
async function loadCatalog() {
  try {
    const res = await fetch("/api/products");
    const data = await res.json();
    els.catalogList.textContent = data.products
      .map((p) => `${p.name} (${money(p.price)})`)
      .join("  ·  ");
    setStatus("Ready", "ok");
  } catch (err) {
    console.error("Catalog load failed:", err);
    els.catalogList.textContent = "failed to load catalog";
    setStatus("Backend error", "err");
    showBanner("Could not reach the server — make sure the backend is running.");
  }
}

// ---------- store info ----------
async function loadStoreInfo() {
  try {
    const res = await fetch("/api/store");
    storeInfo = await res.json();
    els.storeName.textContent = storeInfo.name;
    els.storeBranch.textContent = storeInfo.branch || "";
  } catch (err) {
    console.error("Store info load failed:", err);
  }
}

// ---------- init ----------
loadStoreInfo().then(() => {
  loadCart();
});
loadCatalog();
