const { v4: uuidv4 } = require("uuid");
const crypto = require("crypto");

const GRAPHSHIELD_URL =
  process.env.GRAPHSHIELD_URL || "http://localhost:5000/api/security/check-login";
const GRAPHSHIELD_API_KEY = process.env.GRAPHSHIELD_API_KEY || "DEMO_BANK_KEY";

function normalizeIpAddress(ipAddress) {
  if (!ipAddress) {
    return "127.0.0.1";
  }

  if (ipAddress.startsWith("::ffff:")) {
    return ipAddress.replace("::ffff:", "");
  }

  return ipAddress;
}

function extractDecision(result) {
  if (typeof result?.decision === "string") {
    return result.decision.toUpperCase();
  }

  if (typeof result?.status === "string") {
    return result.status.toUpperCase();
  }

  if (typeof result?.data?.decision === "string") {
    return result.data.decision.toUpperCase();
  }

  return "BLOCK";
}

function hashFingerprint(fingerprint) {
  const data = typeof fingerprint === "string" ? fingerprint : String(fingerprint || "unknown_device_fingerprint");
  return crypto.createHash("sha256").update(data).digest("hex");
}

async function secureLoginCheck(user, req, bank_name, device_fingerprint) {
  const device_id = hashFingerprint(device_fingerprint);
  const payload = {
    user_id: String(user._id),
    device_id,
    ip_address: normalizeIpAddress(req.ip),
    typing_speed: Math.floor(Math.random() * 151) + 150,
    is_vpn: false,
    bank_name,
  };

  const response = await fetch(GRAPHSHIELD_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": GRAPHSHIELD_API_KEY,
    },
    body: JSON.stringify(payload),
  });

  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  if (!response.ok) {
    const message =
      data?.message || `GraphShield request failed with status ${response.status}.`;
    const err = new Error(message);
    err.statusCode = 502;
    err.graphShield = data;
    throw err;
  }

  return {
    decision: extractDecision(data),
    raw: data,
    payload,
  };
}

module.exports = { secureLoginCheck };
