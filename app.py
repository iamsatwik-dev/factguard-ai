import streamlit as st
import pdfplumber
import json
import re
import requests
from datetime import datetime
from groq import Groq

st.set_page_config(
    page_title="FactGuard AI · Automated Fact-Checker",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: #0a192f; color: #e2e8f0; }
  .hero-title {
    font-size: 2.8rem; font-weight: 700;
    background: linear-gradient(90deg, #f55036, #ff8c00);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
  }
  .hero-sub { color: #8b9bb4; font-size: 1.05rem; margin-bottom: 2rem; }
  .card {
    background: #112240; border: 1px solid #1e3a5f;
    border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;
  }
  .card-verified   { border-left: 4px solid #00d4a1; }
  .card-inaccurate { border-left: 4px solid #ffb800; }
  .card-false      { border-left: 4px solid #ff5252; }
  .card-unknown    { border-left: 4px solid #8b9bb4; }
  .badge {
    display: inline-block; padding: 3px 12px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.5px;
  }
  .badge-verified   { background: #003d2e; color: #00d4a1; border: 1px solid #00d4a1; }
  .badge-inaccurate { background: #3d2a00; color: #ffb800; border: 1px solid #ffb800; }
  .badge-false      { background: #3d0a0a; color: #ff5252; border: 1px solid #ff5252; }
  .badge-unknown    { background: #1e2a3a; color: #8b9bb4; border: 1px solid #8b9bb4; }
  .claim-text { color: #e2e8f0; font-size: 1rem; font-style: italic; margin: 0.5rem 0; }
  .verdict-text { color: #cbd5e1; font-size: 0.92rem; line-height: 1.6; }
  .real-fact { color: #00d4a1; font-size: 0.9rem; font-weight: 600; margin-top: 0.5rem; }
  .web-evidence { color: #8b9bb4; font-size: 0.82rem; font-style: italic; margin-top: 0.3rem; }
  .stat-box {
    background: #112240; border: 1px solid #1e3a5f; border-radius: 10px;
    padding: 1rem; text-align: center;
  }
  .stat-num { font-size: 2rem; font-weight: 700; }
  .stat-label { color: #8b9bb4; font-size: 0.82rem; margin-top: 0.2rem; }
  .stButton>button {
    background: linear-gradient(90deg, #f55036, #ff8c00);
    color: white; border: none; border-radius: 8px;
    font-weight: 600; padding: 0.6rem 2rem; font-size: 1rem;
  }
  .stFileUploader { background: #112240 !important; }
  section[data-testid="stFileUploadDropzone"] {
    background: #0d1f3c; border: 2px dashed #1e3a5f; border-radius: 12px;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_pdf_text(pdf_file):
    text_parts = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def clean_json(raw: str) -> str:
    raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    return raw.strip()


def web_search(query: str, serpapi_key: str, num: int = 5) -> list[dict]:
    """Search the live web via SerpAPI and return top snippets."""
    try:
        params = {
            "engine": "google",
            "q": query,
            "api_key": serpapi_key,
            "num": num,
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
        data = resp.json()
        results = []
        for r in data.get("organic_results", [])[:num]:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "link": r.get("link", ""),
            })
        return results
    except Exception:
        return []


def extract_claims(client: Groq, text: str) -> list[dict]:
    prompt = f"""You are a fact-checking expert. Extract up to 15 specific verifiable factual claims from this document.
Focus on: statistics, percentages, dates, financial figures, named entity facts, market sizes.

Return ONLY a valid JSON array, no explanation, no markdown. Each element must have:
{{"claim": "exact claim as stated", "category": "statistic|date|financial|technical|market|other", "context": "brief surrounding context", "search_query": "best 5-word Google query to verify this claim"}}

DOCUMENT:
{text[:6000]}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2500,
    )
    raw = clean_json(response.choices[0].message.content)
    return json.loads(raw)


def verify_claim_with_web(client: Groq, claim: dict, web_results: list[dict]) -> dict:
    web_context = ""
    if web_results:
        web_context = "\n\nLIVE WEB EVIDENCE:\n"
        for i, r in enumerate(web_results, 1):
            web_context += f"{i}. [{r['title']}] {r['snippet']}\n"

    prompt = f"""You are a rigorous fact-checker with access to live web search results. Today's date: {datetime.now().strftime('%B %Y')}.

CLAIM: "{claim['claim']}"
CATEGORY: {claim['category']}
CONTEXT: {claim.get('context', '')}
{web_context}

Based on the web evidence above AND your knowledge, carefully verify this claim.
- Mark VERIFIED if the claim matches current evidence.
- Mark INACCURATE if the stat is outdated (by 2+ years) or partially wrong.
- Mark FALSE if contradicted by evidence or no supporting evidence exists.
- Mark UNVERIFIABLE only if truly impossible to check.

Respond ONLY with a valid JSON object, absolutely no markdown, no extra text:
{{"verdict": "VERIFIED", "confidence": "HIGH", "explanation": "...", "real_fact": null, "source_hint": "...", "web_source": null}}

verdict: VERIFIED | INACCURATE | FALSE | UNVERIFIABLE
confidence: HIGH | MEDIUM | LOW
real_fact: the correct current fact as a string if INACCURATE or FALSE, otherwise null
web_source: the URL of the best supporting web result, or null
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=700,
    )
    raw = clean_json(response.choices[0].message.content)

    if not raw or raw[0] != "{":
        return {
            "verdict": "UNVERIFIABLE", "confidence": "LOW",
            "explanation": "Could not verify this claim.",
            "real_fact": None, "source_hint": "Manual verification recommended",
            "web_source": None,
            "claim": claim["claim"], "category": claim["category"],
            "context": claim.get("context", ""),
        }

    result = json.loads(raw)
    result["claim"] = claim["claim"]
    result["category"] = claim["category"]
    result["context"] = claim.get("context", "")
    return result


def badge_html(verdict: str) -> str:
    cls = verdict.lower() if verdict.lower() in ["verified", "inaccurate", "false"] else "unknown"
    labels = {
        "verified": "✅ VERIFIED",
        "inaccurate": "⚠️ INACCURATE",
        "false": "❌ FALSE",
        "unknown": "❓ UNVERIFIABLE",
    }
    return f'<span class="badge badge-{cls}">{labels.get(cls, verdict)}</span>'


def render_result_card(r: dict):
    verdict = r.get("verdict", "UNVERIFIABLE").lower()
    if verdict not in ["verified", "inaccurate", "false"]:
        verdict = "unknown"

    real_fact_html = (
        f"<p class='real-fact'>📌 Correct fact: {r['real_fact']}</p>"
        if r.get("real_fact") else ""
    )
    web_src_html = (
        f"<p class='web-evidence'>🌐 <a href='{r['web_source']}' target='_blank' style='color:#8b9bb4;'>{r['web_source'][:80]}...</a></p>"
        if r.get("web_source") else ""
    )

    st.markdown(f"""
    <div class="card card-{verdict}">
      {badge_html(verdict.upper())}
      <span style="color:#8b9bb4; font-size:0.78rem; margin-left:0.75rem;">
        Confidence: {r.get('confidence','LOW')} · Category: {r.get('category','').upper()}
      </span>
      <p class="claim-text">"{r.get('claim','')}"</p>
      <p class="verdict-text">{r.get('explanation','')}</p>
      {real_fact_html}
      {web_src_html}
      <p style="color:#475569; font-size:0.8rem; margin-top:0.5rem;">🔍 Verify via: {r.get('source_hint','')}</p>
    </div>
    """, unsafe_allow_html=True)


# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown('<p class="hero-title">🛡️ FactGuard AI</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Upload any PDF · Extract claims · Verify with live web + Groq LLaMA 3.3 70B · Flag inaccuracies instantly</p>',
    unsafe_allow_html=True,
)

# API Keys
with st.expander("🔑 API Keys", expanded=True):
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Get free key → https://console.groq.com",
        )
        st.caption("Free → https://console.groq.com")
    with col_k2:
        serpapi_key = st.text_input(
            "SerpAPI Key (for live web search)",
            type="password",
            placeholder="serpapi_...",
            help="Get free key → https://serpapi.com",
        )
        st.caption("Free → https://serpapi.com (100 searches/month)")

col_upload, col_info = st.columns([3, 2])

with col_upload:
    st.markdown("### 📄 Upload PDF")
    uploaded_file = st.file_uploader("Drop PDF here", type=["pdf"], label_visibility="collapsed")

with col_info:
    st.markdown("### ℹ️ How It Works")
    st.markdown("""
    <div class="card" style="font-size:0.9rem; color:#8b9bb4; line-height:1.9;">
      <b style="color:#f55036;">1. Extract</b> — Reads your PDF, finds verifiable claims<br>
      <b style="color:#f55036;">2. Web Search</b> — Live Google search via SerpAPI<br>
      <b style="color:#f55036;">3. Verify</b> — LLaMA 3.3 70B cross-checks against web evidence<br>
      <b style="color:#f55036;">4. Report</b> — Flags Verified / Inaccurate / False<br><br>
      <span style="color:#ff5252;">⚡ Model: </span>LLaMA 3.3 70B via Groq (Free)<br>
      <span style="color:#ff5252;">🌐 Search: </span>Google via SerpAPI (Live web data)
    </div>
    """, unsafe_allow_html=True)

if uploaded_file and api_key:
    if st.button("🚀 Run Fact-Check"):
        use_web = bool(serpapi_key)
        if not use_web:
            st.warning("⚠️ No SerpAPI key — running in knowledge-only mode (no live web verification).")

        try:
            client = Groq(api_key=api_key)
        except Exception as e:
            st.error(f"Groq setup failed: {e}")
            st.stop()

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        s1 = c1.empty(); s2 = c2.empty(); s3 = c3.empty(); s4 = c4.empty()
        s1.info("⏳ Extracting PDF...")

        try:
            # Step 1: Extract PDF
            pdf_text = extract_pdf_text(uploaded_file)
            if not pdf_text.strip():
                st.error("No text found in PDF. It may be image-based (scanned).")
                st.stop()
            s1.success("✅ PDF extracted")

            # Step 2: Extract claims
            s2.info("⏳ Finding claims...")
            claims = extract_claims(client, pdf_text)
            s2.success(f"✅ Found {len(claims)} claims")

            # Step 3: Web search
            s3.info("⏳ Web searching..." if use_web else "⏳ Skipping web...")
            web_evidence_map: dict[int, list] = {}
            if use_web:
                for i, claim in enumerate(claims):
                    q = claim.get("search_query", claim["claim"][:60])
                    web_evidence_map[i] = web_search(q, serpapi_key, num=4)
            s3.success("✅ Web searched" if use_web else "✅ Skipped (no key)")

            # Step 4: Verify claims
            s4.info("⏳ Verifying...")
            results = []
            bar = st.progress(0)
            status = st.empty()

            for i, claim in enumerate(claims):
                status.markdown(f"*Verifying claim {i+1}/{len(claims)}: {claim['claim'][:60]}...*")
                web_ev = web_evidence_map.get(i, [])
                results.append(verify_claim_with_web(client, claim, web_ev))
                bar.progress((i + 1) / len(claims))

            s4.success("✅ Done!")
            bar.empty(); status.empty()

            # ── Results ──────────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### 📊 Fact-Check Report")

            counts = {"VERIFIED": 0, "INACCURATE": 0, "FALSE": 0, "UNVERIFIABLE": 0}
            for r in results:
                v = r.get("verdict", "UNVERIFIABLE").upper()
                counts[v if v in counts else "UNVERIFIABLE"] += 1

            accuracy = int(counts["VERIFIED"] / len(results) * 100) if results else 0

            ca, cb, cc, cd = st.columns(4)
            with ca:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#00d4a1">{counts["VERIFIED"]}</div><div class="stat-label">✅ Verified</div></div>', unsafe_allow_html=True)
            with cb:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#ffb800">{counts["INACCURATE"]}</div><div class="stat-label">⚠️ Inaccurate</div></div>', unsafe_allow_html=True)
            with cc:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#ff5252">{counts["FALSE"]}</div><div class="stat-label">❌ False</div></div>', unsafe_allow_html=True)
            with cd:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#f55036">{accuracy}%</div><div class="stat-label">📈 Accuracy Score</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            tab1, tab2 = st.tabs([
                f"All Claims ({len(results)})",
                f"Issues Only ({counts['INACCURATE'] + counts['FALSE']})",
            ])

            with tab1:
                for r in results:
                    render_result_card(r)

            with tab2:
                issues = [r for r in results if r.get("verdict", "").upper() in ["INACCURATE", "FALSE"]]
                if issues:
                    for r in issues:
                        render_result_card(r)
                else:
                    st.success("🎉 No issues found — all claims verified!")

            # Download
            report = {
                "generated_at": datetime.now().isoformat(),
                "file": uploaded_file.name,
                "model": "llama-3.3-70b-versatile (Groq)",
                "web_search_enabled": use_web,
                "summary": counts,
                "accuracy_score": accuracy,
                "claims": results,
            }
            st.download_button(
                "⬇️ Download Report (JSON)",
                data=json.dumps(report, indent=2),
                file_name=f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
            )

        except json.JSONDecodeError:
            st.error("JSON parsing error — the model returned unexpected output. Please try again.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

elif uploaded_file and not api_key:
    st.warning("Please enter your Groq API key above.")
else:
    st.markdown("""
    <div class="card" style="text-align:center; padding:2.5rem;">
      <div style="font-size:3rem;">📄</div>
      <div style="color:#8b9bb4; margin-top:0.5rem;">Upload a PDF to begin fact-checking</div>
      <div style="color:#475569; font-size:0.85rem; margin-top:0.3rem;">Works with reports, decks, whitepapers, press releases</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    '<p style="color:#475569; font-size:0.8rem; text-align:center;">FactGuard AI · Powered by LLaMA 3.3 70B via Groq · Live Web Verification via SerpAPI · 100% Free</p>',
    unsafe_allow_html=True,
)
