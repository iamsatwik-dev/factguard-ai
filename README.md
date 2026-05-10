# 🛡️ FactGuard AI — Automated Fact-Checker

> Upload a PDF → Extract claims → Verify against **live web** → Flag inaccuracies instantly

---

## 🚀 Live Demo

**Deployed App:** [your-app.streamlit.app](https://factguard-ai.streamlit.app/)

---

## ✨ Features

| Feature | Detail |
|---|---|
| 📄 PDF Upload | Drag-and-drop any PDF report, whitepaper, or deck |
| 🔍 Claim Extraction | LLaMA 3.3 70B extracts up to 15 verifiable claims |
| 🌐 Live Web Search | SerpAPI searches Google for real-time evidence |
| ✅ Verification | Cross-references claims against live web + model knowledge |
| 🏷️ Verdicts | **VERIFIED** / **INACCURATE** / **FALSE** / **UNVERIFIABLE** |
| 📊 Report | Visual dashboard + downloadable JSON report |

---

## 🧠 How It Works

```
PDF → pdfplumber → raw text
         ↓
  LLaMA 3.3 70B → extract claims + search queries
         ↓
  SerpAPI → live Google results for each claim
         ↓
  LLaMA 3.3 70B → verify claim vs web evidence
         ↓
  Streamlit UI → display verdicts + download JSON
```

---

## 🔧 Setup

### 1. Clone the repo

```bash
git clone https://github.com/iamsatwik-dev/factguard-ai
cd factguard-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get API keys (both free)

- **Groq API Key** → [console.groq.com](https://console.groq.com) — LLaMA 3.3 70B (free tier)
- **SerpAPI Key** → [serpapi.com](https://serpapi.com) — 100 free searches/month

### 4. Run locally

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🌐 Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"** → Select your repo → `app.py`
4. Click **Deploy** — live in ~60 seconds ✅

> No secrets needed in `.streamlit/secrets.toml` — users enter API keys in the UI.

---

## 📁 Project Structure

```
factguard-ai/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## 🧪 Evaluation (Trap Document Test)

The app is designed to catch:
- **Outdated statistics** (e.g., "ChatGPT has 100M users" — now 500M+)
- **Fabricated figures** (hallucinated market sizes, wrong dates)
- **False attributions** (wrong company/person for a fact)

Each claim shows:
- Verdict badge (color-coded)
- Confidence level
- Explanation with evidence
- Correct real fact (if inaccurate/false)
- Live web source URL

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| PDF Parsing | pdfplumber |
| LLM | LLaMA 3.3 70B via Groq API |
| Web Search | Google via SerpAPI |
| Deployment | Streamlit Cloud |

---

## 📝 License

MIT License — free to use and modify.
