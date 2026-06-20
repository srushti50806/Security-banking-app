require("dotenv").config();

const path = require("path");
const express = require("express");
const mongoose = require("mongoose");
const bcrypt = require("bcrypt");
const jwt = require("jsonwebtoken");

const User = require("./models/User");
const { requireAuth } = require("./middleware/auth");
const { secureLoginCheck } = require("./services/graphShield");

const app = express();
const PORT = process.env.PORT || 3000;
const MONGODB_URI =
  process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/demo_bank";
const BANK_NAME = process.env.BANK_NAME || "Demo Bank";

app.set("trust proxy", true);
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(express.static(path.join(__dirname, "public")));

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function createToken(user) {
  return jwt.sign(
    {
      userId: String(user._id),
      email: user.email,
      username: user.username,
    },
    process.env.JWT_SECRET,
    { expiresIn: "1h" }
  );
}

app.post("/api/auth/register", async (req, res) => {
  try {
    const { username, email, password } = req.body;

    if (!username || !email || !password) {
      return res
        .status(400)
        .json({ message: "Username, email, and password are required." });
    }

    if (String(username).trim().length < 3) {
      return res
        .status(400)
        .json({ message: "Username must be at least 3 characters long." });
    }

    if (!isValidEmail(email)) {
      return res.status(400).json({ message: "Enter a valid email address." });
    }

    if (String(password).length < 8) {
      return res
        .status(400)
        .json({ message: "Password must be at least 8 characters long." });
    }

    const existingUser = await User.findOne({ email: email.toLowerCase() });
    if (existingUser) {
      return res.status(409).json({ message: "Email is already registered." });
    }

    const passwordHash = await bcrypt.hash(password, 12);
    const user = await User.create({
      username: username.trim(),
      email: email.toLowerCase(),
      passwordHash,
    });

    return res.status(201).json({
      message: "Registration successful.",
      user: {
        user_id: String(user._id),
        username: user.username,
        email: user.email,
      },
    });
  } catch (error) {
    return res.status(500).json({ message: "Registration failed." });
  }
});

app.post("/api/auth/login", async (req, res) => {
  try {
    const { email, password, bank_name: providedBankName, device_fingerprint } = req.body;
    const bank_name = providedBankName || BANK_NAME;

    if (!email || !password) {
      return res.status(400).json({ message: "Email and password are required." });
    }

    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) {
      return res.status(401).json({ message: "Invalid email or password." });
    }

    const passwordMatches = await bcrypt.compare(password, user.passwordHash);
    if (!passwordMatches) {
      return res.status(401).json({ message: "Invalid email or password." });
    }

    const securityResult = await secureLoginCheck(user, req, bank_name, device_fingerprint);

    if (securityResult.decision !== "ALLOW") {
      return res.status(403).json({
        message: "Login blocked by GraphShield.",
        decision: securityResult.decision,
      });
    }

    const token = createToken(user);

    return res.json({
      message: "Login successful.",
      decision: securityResult.decision,
      token,
      user: {
        user_id: String(user._id),
        username: user.username,
        email: user.email,
      },
    });
  } catch (error) {
    const statusCode = error.statusCode || 500;
    const message =
      statusCode === 502
        ? "Security verification failed. Please try again later."
        : "Login failed.";

    return res.status(statusCode).json({ message });
  }
});

app.get("/api/auth/me", requireAuth, async (req, res) => {
  try {
    const user = await User.findById(req.auth.userId).select("_id username email");

    if (!user) {
      return res.status(404).json({ message: "User not found." });
    }

    return res.json({
      user: {
        user_id: String(user._id),
        username: user.username,
        email: user.email,
      },
    });
  } catch (error) {
    return res.status(500).json({ message: "Unable to load user profile." });
  }
});

app.get("/dashboard", (req, res) => {
  return res.sendFile(path.join(__dirname, "public", "dashboard.html"));
});

app.use((req, res) => {
  return res.status(404).json({ message: "Route not found." });
});

async function startServer() {
  if (!process.env.JWT_SECRET) {
    throw new Error("JWT_SECRET is required. Add it to your environment.");
  }

  await mongoose.connect(MONGODB_URI);

  app.listen(PORT, () => {
    console.log(`Demo Bank server running on http://localhost:${PORT}`);
  });
}

startServer().catch((error) => {
  console.error("Failed to start server:", error.message);
  process.exit(1);
});
