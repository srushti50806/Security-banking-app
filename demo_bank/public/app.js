const registerForm = document.getElementById("registerForm");
const loginForm = document.getElementById("loginForm");
const statusBox = document.getElementById("status");

function showStatus(message, type = "success") {
  statusBox.textContent = message;
  statusBox.className = `status is-visible ${type === "error" ? "is-error" : "is-success"}`;
}

function getFormPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function generateDeviceFingerprint() {
  const fingerprint = {
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    screenWidth: screen.width,
    screenHeight: screen.height,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
  // Simple hash function
  const str = JSON.stringify(fingerprint);
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash.toString(16);
}

async function handleJsonRequest(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.message || "Request failed.");
  }

  return data;
}

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const data = await handleJsonRequest("/api/auth/register", getFormPayload(registerForm));
    showStatus(data.message || "Registration successful.");
    registerForm.reset();
  } catch (error) {
    showStatus(error.message, "error");
  }
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const payload = getFormPayload(loginForm);
    payload.device_fingerprint = generateDeviceFingerprint();
    const data = await handleJsonRequest("/api/auth/login", payload);
    localStorage.setItem("demo_bank_token", data.token);
    showStatus("Login approved. Redirecting to dashboard.");
    window.location.assign("/dashboard");
  } catch (error) {
    showStatus(error.message, "error");
  }
});

