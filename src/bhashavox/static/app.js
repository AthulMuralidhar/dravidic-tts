const form = document.querySelector("#speech-form");
const textInput = document.querySelector("#text");
const characterCount = document.querySelector("#character-count");
const providerStatus = document.querySelector("#provider-status");
const testModeWarning = document.querySelector("#test-mode-warning");
const voiceSelect = document.querySelector("#voice");
const voiceHelp = document.querySelector("#voice-help");
const speedInput = document.querySelector("#speed");
const speedOutput = document.querySelector("#speed-output");
const message = document.querySelector("#message");
const generateButton = document.querySelector("#generate");
const resultPanel = document.querySelector("#result");
const audio = document.querySelector("#audio");
const download = document.querySelector("#download");

let capabilities = null;
let audioUrl = null;

function selectedLanguage() {
  return form.elements.language.value;
}

function updateCharacterCount() {
  const limit = capabilities?.max_characters ?? 5000;
  const count = Array.from(textInput.value).length;
  characterCount.textContent = `${count.toLocaleString()} / ${limit.toLocaleString()}`;
  characterCount.style.color = count > limit ? "#b33720" : "";
}

function updateVoices() {
  const language = selectedLanguage();
  voiceSelect.replaceChildren();

  if (language === "auto") {
    voiceSelect.add(new Option("Automatic by script", ""));
    voiceSelect.disabled = true;
    voiceHelp.textContent = "Choose a language to select its voice.";
    return;
  }

  const voices = (capabilities?.voices ?? []).filter(
    (voice) => voice.language === language,
  );
  for (const voice of voices) {
    voiceSelect.add(new Option(voice.label, voice.id));
  }
  voiceSelect.disabled = voices.length === 0;
  voiceHelp.textContent = voices.length
    ? `${voices.length} voice${voices.length === 1 ? "" : "s"} available.`
    : "This speech engine chooses the voice automatically.";
}

function setBusy(busy) {
  generateButton.disabled = busy;
  generateButton.firstElementChild.textContent = busy
    ? "Generating…"
    : capabilities?.provider === "tone"
      ? "Generate test tone"
      : "Generate speech";
}

async function loadCapabilities() {
  try {
    const response = await fetch("/api/v1/capabilities");
    if (!response.ok) throw new Error("Capabilities could not be loaded.");
    capabilities = await response.json();
    providerStatus.classList.toggle("ready", capabilities.ready);
    providerStatus.classList.toggle("unavailable", !capabilities.ready);
    providerStatus.lastChild.textContent = capabilities.ready
      ? ` ${capabilities.provider} ready`
      : ` ${capabilities.provider} unavailable`;
    const testMode = capabilities.provider === "tone";
    testModeWarning.hidden = !testMode;
    generateButton.firstElementChild.textContent = testMode
      ? "Generate test tone"
      : "Generate speech";
    generateButton.disabled = !capabilities.ready;
    updateCharacterCount();
    updateVoices();
  } catch (error) {
    providerStatus.classList.add("unavailable");
    providerStatus.lastChild.textContent = " Service unavailable";
    message.textContent = error.message;
    generateButton.disabled = true;
  }
}

function readError(response, body) {
  if (body?.detail) {
    if (Array.isArray(body.detail)) {
      return body.detail.map((item) => item.msg).join(" ");
    }
    return body.detail;
  }
  return `Speech generation failed (${response.status}).`;
}

form.addEventListener("change", (event) => {
  if (event.target.name === "language") updateVoices();
});

textInput.addEventListener("input", updateCharacterCount);
speedInput.addEventListener("input", () => {
  speedOutput.value = `${Number(speedInput.value).toFixed(1)}×`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";
  resultPanel.hidden = true;

  const text = textInput.value;
  const limit = capabilities?.max_characters ?? 5000;
  if (!text.trim()) {
    message.textContent = "Paste some text first.";
    textInput.focus();
    return;
  }
  if (Array.from(text).length > limit) {
    message.textContent = `Keep the text under ${limit.toLocaleString()} characters.`;
    textInput.focus();
    return;
  }

  setBusy(true);
  try {
    const language = selectedLanguage();
    const payload = {
      text,
      language,
      voice: language === "auto" ? null : voiceSelect.value || null,
      speed: Number(speedInput.value),
      format: "wav",
    };
    const response = await fetch("/api/v1/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let body = null;
      try {
        body = await response.json();
      } catch {
        // The fallback below includes the HTTP status.
      }
      throw new Error(readError(response, body));
    }

    const blob = await response.blob();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = URL.createObjectURL(blob);
    audio.src = audioUrl;
    download.href = audioUrl;
    resultPanel.hidden = false;
    resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    await audio.play().catch(() => undefined);
  } catch (error) {
    message.textContent = error.message || "Speech generation failed.";
  } finally {
    setBusy(false);
  }
});

window.addEventListener("beforeunload", () => {
  if (audioUrl) URL.revokeObjectURL(audioUrl);
});

updateCharacterCount();
loadCapabilities();
