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
const activeJobKey = "bhashavox.activeSpeechJob";

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

function setBusy(busy, label = "Generating…") {
  generateButton.disabled = busy;
  generateButton.firstElementChild.textContent = busy
    ? label
    : capabilities?.provider === "tone"
      ? "Generate test tone"
      : "Generate speech";
}

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
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
    const activeJobId = window.localStorage.getItem(activeJobKey);
    if (activeJobId) {
      trackJob(activeJobId).catch((error) => {
        message.textContent = error.message || "Speech generation failed.";
        setBusy(false);
      });
    }
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

async function responseError(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    // readError includes the HTTP status when no JSON body is available.
  }
  return new Error(readError(response, body));
}

async function loadCompletedAudio(job) {
  while (true) {
    try {
      const response = await fetch(job.audio_url, { cache: "no-store" });
      if (!response.ok) throw await responseError(response);
      const blob = await response.blob();
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      audioUrl = URL.createObjectURL(blob);
      audio.src = audioUrl;
      download.href = audioUrl;
      resultPanel.hidden = false;
      resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      message.textContent = job.text_corrected
        ? "Ready. Copy/paste damage was corrected before speech."
        : "Your speech is ready.";
      await audio.play().catch(() => undefined);
      return;
    } catch (error) {
      if (error.message && !error.message.includes("Failed to fetch")) {
        throw error;
      }
      message.textContent = "Audio is ready. Reconnecting to download it…";
      await wait(3000);
    }
  }
}

async function trackJob(jobId) {
  window.localStorage.setItem(activeJobKey, jobId);
  setBusy(true, "Checking job…");

  while (true) {
    let job;
    try {
      const response = await fetch(`/api/v1/speech/jobs/${jobId}`, {
        cache: "no-store",
      });
      if (!response.ok) throw await responseError(response);
      job = await response.json();
    } catch (error) {
      if (error.message && !error.message.includes("Failed to fetch")) {
        window.localStorage.removeItem(activeJobKey);
        setBusy(false);
        throw error;
      }
      setBusy(true, "Reconnecting…");
      message.textContent =
        "Connection interrupted. Generation continues on the laptop; reconnecting…";
      await wait(3000);
      continue;
    }

    if (job.status === "queued") {
      setBusy(true, "Queued…");
      message.textContent = "Queued on the laptop. You can leave this page and return.";
    } else if (job.status === "running") {
      setBusy(true, "Generating…");
      const progress = job.chunks_total
        ? ` Chunk ${Math.min(job.chunks_completed + 1, job.chunks_total)} of ${job.chunks_total}.`
        : "";
      message.textContent = `Generating on the laptop.${progress} You can leave this page and return.`;
    } else if (job.status === "failed") {
      window.localStorage.removeItem(activeJobKey);
      setBusy(false);
      throw new Error(job.error || "Speech generation failed.");
    } else if (job.status === "completed") {
      await loadCompletedAudio(job);
      window.localStorage.removeItem(activeJobKey);
      setBusy(false);
      return;
    }

    await wait(2000);
  }
}

form.addEventListener("change", (event) => {
  if (event.target.name === "language") updateVoices();
});

textInput.addEventListener("input", () => {
  updateCharacterCount();
});
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
    const response = await fetch("/api/v1/speech/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw await responseError(response);
    const job = await response.json();
    await trackJob(job.id);
  } catch (error) {
    message.textContent = error.message || "Speech generation failed.";
  } finally {
    if (!window.localStorage.getItem(activeJobKey)) setBusy(false);
  }
});

window.addEventListener("beforeunload", () => {
  if (audioUrl) URL.revokeObjectURL(audioUrl);
});

updateCharacterCount();
loadCapabilities();
