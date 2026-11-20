(() => {
  "use strict";

  const CFG = {
    intervalMs: 350,     // cada cuánto se envía un fotograma
    minConfidence: 0.6,  // confianza mínima para aceptar una letra
    holdFrames: 4,       // fotogramas seguidos para confirmar
    repeatFrames: 14,    // fotogramas para repetir la misma letra (LL, RR...)
    size: 256,           // lado del recorte enviado al servidor (px)
    crop: 0.82,          // fracción del video usada; coincide con el recuadro guía
    maxErrors: 3,        // fallos de red seguidos antes de avisar
  };
  const $ = (id) => document.getElementById(id);
  const { alphabet, available, imgUrl } = document.body.dataset;
  const ALPHABET = JSON.parse(alphabet), AVAILABLE = JSON.parse(available);

  let stream = null, timer = null, busy = false, errors = 0;
  let text = "", candidate = null, count = 0, lastCommitted = null;

  const showAlert = (msg) => { $("alert").textContent = msg; $("alert").hidden = false; };
  const hideAlert = () => { $("alert").hidden = true; };

  // ---------- Pestañas (con teclado) ----------
  const tabs = [...document.querySelectorAll(".tab")];
  function selectTab(tab, focus) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
    });
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("is-active", p.id === "tab-" + tab.dataset.tab));
    if (focus) tab.focus();
  }
  tabs.forEach((tab, i) => {
    tab.onclick = () => selectTab(tab);
    tab.onkeydown = (e) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (step) { e.preventDefault(); selectTab(tabs[(i + step + tabs.length) % tabs.length], true); }
    };
  });

  // ---------- Cámara ----------
  const CAMERA_ERRORS = {
    NotAllowedError: "Permiso de cámara denegado. Habilítalo en el navegador.",
    NotFoundError: "No se encontró ninguna cámara conectada.",
    NotReadableError: "La cámara está siendo usada por otra aplicación.",
  };

  function setCameraUI(on) {
    $("videoWrap").classList.toggle("is-on", on);
    $("statusPill").classList.toggle("is-live", on);
    $("btnCamera").classList.toggle("is-stop", on);
    $("btnCamera").textContent = on ? "Detener cámara" : "Activar cámara";
    $("statusText").textContent = on ? "Cámara activa" : "Cámara apagada";
    if (!on) $("detected").hidden = true;
  }

  async function startCamera() {
    hideAlert();
    if (!navigator.mediaDevices?.getUserMedia) return showAlert("Tu navegador no permite usar la cámara. Abre la app desde localhost o HTTPS.");
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 960 }, height: { ideal: 720 }, facingMode: "user" }, audio: false });
    } catch (err) {
      return showAlert(CAMERA_ERRORS[err.name] || "No se pudo acceder a la cámara.");
    }
    $("video").srcObject = stream;
    setCameraUI(true);
    errors = 0;
    timer = setInterval(sendFrame, CFG.intervalMs);
  }

  function stopCamera() {
    clearInterval(timer);
    stream?.getTracks().forEach((t) => t.stop());
    stream = null;
    $("video").srcObject = null;
    setCameraUI(false);
    resetHold();
  }

  $("btnCamera").onclick = () => (stream ? stopCamera() : startCamera());
  // Privacidad: apagar la cámara si el usuario se va de la página
  document.addEventListener("visibilitychange", () => document.hidden && stream && stopCamera());
  window.addEventListener("pagehide", () => stream && stopCamera());

  // ---------- Captura y predicción ----------
  function captureFrame() {
    const v = $("video");
    if (!v.videoWidth) return null;
    const side = Math.min(v.videoWidth, v.videoHeight) * CFG.crop;   // recorte cuadrado central
    const c = $("canvas");
    c.width = c.height = CFG.size;
    const ctx = c.getContext("2d");
    ctx.save();
    ctx.translate(CFG.size, 0);
    ctx.scale(-1, 1);   // efecto espejo: igual que cv2.flip(frame, 1) en camara.py
    ctx.drawImage(v, (v.videoWidth - side) / 2, (v.videoHeight - side) / 2, side, side, 0, 0, CFG.size, CFG.size);
    ctx.restore();
    return c.toDataURL("image/jpeg", 0.8);
  }

  async function sendFrame() {
    const image = busy ? null : captureFrame();
    if (!image) return;
    busy = true;
    try {
      const res = await fetch("/api/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ image }) });
      if (!res.ok) throw new Error(res.status);
      handlePrediction(await res.json());
      errors = 0;
      hideAlert();
    } catch {
      if (++errors >= CFG.maxErrors) {
        $("statusText").textContent = "Sin conexión con el servidor";
        showAlert("No hay respuesta del servidor. Verifica que la aplicación siga en ejecución.");
      }
    } finally {
      busy = false;
    }
  }

  function handlePrediction({ demo, letter, confidence }) {
    if (demo) { $("statusText").textContent = "Modo demostración"; return; }
    $("statusText").textContent = "Cámara activa";
    $("detected").hidden = !letter;
    if (letter) {
      const pct = Math.round(confidence * 100);
      $("detectedLetter").textContent = letter;
      $("confBar").style.width = pct + "%";
      $("confText").textContent = pct + "%";
    }
    if (!letter || confidence < CFG.minConfidence) { resetHold(); lastCommitted = null; return; }

    count = letter === candidate ? count + 1 : 1;
    candidate = letter;
    const needed = letter === lastCommitted ? CFG.repeatFrames : CFG.holdFrames;
    $("holdBar").style.width = Math.min(100, (count / needed) * 100) + "%";
    if (count >= needed) { addChar(letter); lastCommitted = letter; count = 0; }
  }

  function resetHold() { candidate = null; count = 0; $("holdBar").style.width = "0%"; }

  // ---------- Texto reconocido ----------
  function renderOutput() {
    if (!text) {
      $("output").innerHTML = '<span class="output-empty">Las letras reconocidas aparecerán aquí…</span>';
      return;
    }
    $("output").textContent = text;
    $("output").insertAdjacentHTML("beforeend", '<span class="caret"></span>');
  }
  const addChar = (c) => { text += c; renderOutput(); };

  $("btnSpace").onclick = () => addChar(" ");
  $("btnDelete").onclick = () => { text = text.slice(0, -1); renderOutput(); };
  $("btnClear").onclick = () => { text = ""; lastCommitted = null; renderOutput(); };

  $("btnSpeak").onclick = () => {
    if (!text.trim()) return;
    if (!("speechSynthesis" in window)) return showAlert("Tu navegador no soporta lectura en voz alta.");
    const u = new SpeechSynthesisUtterance(text.toLowerCase());
    u.lang = "es-CO";
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  };

  $("btnCopy").onclick = async () => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      $("btnCopy").textContent = "¡Copiado!";
      setTimeout(() => ($("btnCopy").textContent = "Copiar"), 1200);
    } catch {
      showAlert("No se pudo copiar: el navegador no concedió acceso al portapapeles.");
    }
  };

  // ---------- Texto → Seña y alfabeto ----------
  // Quita tildes y diéresis pero conserva la Ñ
  const normalize = (s) =>
    s.toUpperCase().replace(/Ñ/g, "\u0001").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\u0001/g, "Ñ");

  function signTile(ch) {
    const tile = document.createElement("figure");
    tile.className = "sign";
    tile.innerHTML = AVAILABLE[ch]
      ? `<img src="${imgUrl}${AVAILABLE[ch]}" alt="Seña de la letra ${ch}" loading="lazy">`
      : '<div class="no-img">Seña con<br>movimiento</div>';
    tile.insertAdjacentHTML("beforeend", `<figcaption>${ch}</figcaption>`);
    return tile;
  }

  const HINT = '<p class="muted">Aquí verás la secuencia de señas.</p>';
  $("signRow").innerHTML = HINT;
  $("textInput").oninput = (e) => {
    const words = normalize(e.target.value).split(/\s+/).filter(Boolean);
    $("signRow").innerHTML = words.length ? "" : HINT;
    words.forEach((word) => {
      const box = document.createElement("div");
      box.className = "word";
      [...word].filter((c) => ALPHABET.includes(c)).forEach((c) => box.appendChild(signTile(c)));
      $("signRow").appendChild(box);
    });
  };

  ALPHABET.forEach((ch) => $("alphaGrid").appendChild(signTile(ch)));
  renderOutput();
})();