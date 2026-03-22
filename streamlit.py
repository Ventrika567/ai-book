import pandas as pd
import requests
import streamlit as st
from html import escape

API_BASE = "http://localhost:8001"

st.set_page_config(page_title="Rent Smart", layout="centered")

# ---------- Session State ----------
if "extraction" not in st.session_state:
    st.session_state.extraction = None
if "provider_results" not in st.session_state:
    st.session_state.provider_results = None
if "best_selections" not in st.session_state:
    st.session_state.best_selections = None
if "final_results" not in st.session_state:
    st.session_state.final_results = None

# ---------- CSS ----------
st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(circle at top, rgba(255, 255, 255, 0.35), transparent 34%),
            linear-gradient(180deg, #f4e8ff 0%, #ead7ff 52%, #e2cbff 100%);
    }
    .center-text {
        text-align: center;
        color: #221433;
        font-family: sans-serif;
    }
    .brand-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.9rem;
        margin-top: 0.8rem;
    }
    .brand-book {
        width: 66px;
        height: 66px;
        border-radius: 18px;
        background: linear-gradient(145deg, #8f63d9 0%, #b891f5 100%);
        position: relative;
        box-shadow: 0 18px 32px rgba(106, 70, 168, 0.22);
    }
    .brand-book::before {
        content: "";
        position: absolute;
        top: 8px;
        bottom: 8px;
        left: 13px;
        width: 8px;
        border-radius: 8px;
        background: rgba(61, 31, 110, 0.32);
    }
    .brand-book::after {
        content: "";
        position: absolute;
        top: 12px;
        left: 25px;
        width: 26px;
        height: 42px;
        border-radius: 4px 10px 10px 4px;
        background: rgba(255, 255, 255, 0.9);
    }
    .brand-name {
        font-size: clamp(2rem, 5vw, 3.4rem);
        line-height: 1;
        font-weight: 900;
        letter-spacing: 0.02em;
        color: #3e215f;
    }
    .stApp .main-title {
        font-size: min(5rem, 9vw) !important;
        font-weight: 900 !important;
        line-height: 1.05 !important;
        margin-bottom: 0px !important;
    }
    .sub-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: -10px;
    }
    .description {
        font-size: 1.1rem;
        margin-bottom: 40px;
    }
    .section-title {
        color: #000000 !important;
        font-weight: 800;
        font-size: 1.35rem;
        margin-top: 1.2rem;
        margin-bottom: 0.55rem;
    }
    .section-copy { color: #000000; }
    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 0.85rem;
        margin-bottom: 0.75rem;
    }
    .info-card {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(123, 123, 123, 0.18);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        box-shadow: 0 10px 24px rgba(72, 72, 72, 0.08);
        color: #000000;
    }
    .info-card-label {
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #575757;
        margin-bottom: 0.3rem;
    }
    .info-card-value {
        font-size: 1rem;
        font-weight: 700;
        color: #000000;
    }
    .provider-card {
        background: #ffffff;
        border: 1px solid rgba(126, 126, 126, 0.2);
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 12px 28px rgba(82, 82, 82, 0.1);
        color: #000000;
        margin-top: 0.65rem;
    }
    .provider-topline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.8rem;
    }
    .provider-name {
        font-size: 1.05rem;
        font-weight: 800;
        color: #000000;
    }
    .provider-pill {
        display: inline-block;
        background: #ececec;
        color: #000000;
        border-radius: 999px;
        padding: 0.28rem 0.7rem;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .profile-box [data-testid="stVerticalBlockBorderWrapper"] {
        border: 4px solid #000000 !important;
        border-radius: 22px !important;
        background: rgba(255, 255, 255, 0.18) !important;
        box-shadow: 0 14px 28px rgba(90, 90, 90, 0.08);
    }
    .profile-box [data-testid="stVerticalBlockBorderWrapper"] > div {
        border: 4px solid #000000 !important;
        border-radius: 22px !important;
    }
    .chat-shell {
        background: linear-gradient(180deg, rgba(221, 221, 221, 0.96) 0%, rgba(206, 206, 206, 0.96) 100%);
        border: 1px solid rgba(120, 120, 120, 0.35);
        border-radius: 24px;
        box-shadow: 0 24px 40px rgba(88, 88, 88, 0.2);
        padding: 1rem 1rem 0.8rem 1rem;
    }
    .chat-shell .section-title { margin-top: 0; font-size: 1.15rem; }
    .chat-scroll {
        max-height: 420px;
        overflow-y: auto;
        padding-right: 0.2rem;
        margin-bottom: 0.5rem;
    }
    .chat-bubble {
        border-radius: 20px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.9rem;
        box-shadow: 0 10px 22px rgba(93, 93, 93, 0.08);
        border: 1px solid rgba(126, 126, 126, 0.18);
    }
    .chat-bubble.user {
        background: rgba(120, 110, 130, 0.5);
        margin-left: 1.2rem;
    }
    .chat-bubble.assistant {
        background: rgba(255, 255, 255, 0.88);
        margin-right: 1.2rem;
    }
    .chat-role {
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #555555;
        margin-bottom: 0.35rem;
    }
    .chat-content {
        color: #000000;
        line-height: 1.55;
        white-space: pre-wrap;
    }
    .chat-content p { margin: 0; color: #000000; }
    .chat-input-shell {
        background: rgba(255, 255, 255, 0.85);
        border-radius: 18px;
        padding: 0.65rem;
        border: 1px solid rgba(115, 115, 115, 0.18);
        margin-top: 0.25rem;
    }
    .chat-panel [data-testid="stVerticalBlockBorderWrapper"] {
        position: fixed !important;
        right: 1.25rem;
        bottom: 1.25rem;
        width: min(460px, calc(100vw - 2rem));
        z-index: 1000;
        background: linear-gradient(180deg, rgba(221, 221, 221, 0.96) 0%, rgba(206, 206, 206, 0.96) 100%) !important;
        border: 1px solid rgba(120, 120, 120, 0.35) !important;
        border-radius: 24px !important;
        box-shadow: 0 24px 40px rgba(88, 88, 88, 0.2);
    }
    .chat-panel [data-testid="stVerticalBlockBorderWrapper"] > div {
        background: transparent !important;
    }
    @media (max-width: 768px) {
        .chat-panel [data-testid="stVerticalBlockBorderWrapper"] {
            right: 0.75rem;
            bottom: 0.75rem;
            width: calc(100vw - 1.5rem);
        }
        .chat-scroll { max-height: 300px; }
    }
    [data-testid="stFileUploader"] {
        color: #000000;
        max-width: 760px;
        margin: 0 auto 0.5rem auto;
    }
    [data-testid="stFileUploader"] section {
        color: #000000;
        border-radius: 22px;
        border: 2px dashed #8c63cf;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.72) 0%, rgba(243, 232, 255, 0.94) 100%);
        box-shadow: 0 12px 30px rgba(74, 54, 124, 0.12);
        padding: 0.5rem 0.85rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: #6e42b5;
        box-shadow: 0 16px 36px rgba(74, 54, 124, 0.2);
        transform: translateY(-1px);
    }
    [data-testid="stFileUploader"] * { color: #000000 !important; }
    [data-testid="stFileUploaderFile"] *,
    [data-testid="stFileUploaderDropzone"] * { color: #000000 !important; }
    [data-testid="stBaseButton-secondary"] { color: #ffffff !important; }
    [data-testid="stBaseButton-secondary"] * { color: #ffffff !important; }
    .chat-shell textarea,
    .chat-shell textarea:focus {
        background: #ffffff !important;
        color: #000000 !important;
    }
    label, .stTextArea label, .stTextInput label, .stSelectbox label { color: #000000 !important; }
    [data-testid="stWidgetLabel"] * { color: #000000 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background:
            repeating-linear-gradient(
                -45deg,
                rgba(242, 242, 242, 0.95),
                rgba(242, 242, 242, 0.95) 12px,
                rgba(227, 227, 227, 0.95) 12px,
                rgba(227, 227, 227, 0.95) 24px
            );
        border: 1px solid rgba(132, 132, 132, 0.3) !important;
        border-radius: 22px !important;
        box-shadow: 0 14px 28px rgba(90, 90, 90, 0.08);
    }
    [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.74) !important;
        border: 1px solid rgba(122, 84, 181, 0.22) !important;
        border-radius: 18px !important;
    }
    [data-testid="stExpander"] * { color: #000000 !important; }
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] details > div {
        background: rgba(255, 255, 255, 0.74) !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown(
    """
    <div class="brand-wrap">
        <div class="brand-book"></div>
        <div class="brand-name">SmartRent</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('<p class="center-text sub-title">RENT SMART - PAY LESS</p>', unsafe_allow_html=True)
st.markdown('<p class="center-text main-title">Your Optimized Textbook Rental Engine</p>', unsafe_allow_html=True)
st.markdown('<p class="center-text description">Upload your syllabus and let our AI calculate your active reading dates to find the cheapest micro-rental.<br><b>You only pay</b> for the time you need!</p>', unsafe_allow_html=True)

# ---------- File Upload ----------
uploaded_file = st.file_uploader("DRAG/DROP YOUR FILES HERE", type=["pdf"], label_visibility="hidden")



# ---------- Analysis Pipeline ----------
if uploaded_file is not None:
    if st.button("Analyze Syllabus", width="stretch", type="primary"):
        try:
            st.markdown('<div class="section-title">Analysis Pipeline</div>', unsafe_allow_html=True)
            pipeline_container = st.container(border=True)
            
            with pipeline_container:
                step1_ui = st.empty()
                step2_ui = st.empty()
                step3_ui = st.empty()
                step4_ui = st.empty()

                step1_ui.info("⏳ Step 1/4: Extracting books and schedule from PDF...")
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                resp = requests.post(f"{API_BASE}/extract-syllabus", files=files, timeout=120)
                if resp.status_code != 200:
                    step1_ui.error(f"Extraction failed ({resp.status_code}): {resp.text}")
                    st.stop()
                extraction = resp.json()
                st.session_state.extraction = extraction
                books = extraction.get("books", [])
                schedule_items = extraction.get("schedule_items", [])
                if not books:
                    step1_ui.error("❌ Step 1/4: No textbooks detected.")
                    st.stop()
                step1_ui.success(f"✅ Step 1/4: Found **{len(books)}** books and **{len(schedule_items)}** schedule items in syllabus.")

                step2_ui.info(f"⏳ Step 2/4: Querying API search engines for {len(books)} books...")
                resp = requests.post(f"{API_BASE}/query-providers", json={"books": books}, timeout=180)
                if resp.status_code != 200:
                    step2_ui.error(f"Provider query failed ({resp.status_code}): {resp.text}")
                    st.stop()
                provider_results = resp.json()
                st.session_state.provider_results = provider_results
                total_providers = sum(len(r.get("providers", [])) for r in provider_results)
                step2_ui.success(f"✅ Step 2/4: Retrieved **{total_providers}** provider matches across open APIs.")

                step3_ui.info("⏳ Step 3/4: Selecting best providers using AI...")
                book_results = [{"bookname": r.get("bookname", ""), "providers": r.get("providers", [])} for r in provider_results]
                resp = requests.post(f"{API_BASE}/select-best-provider", json={"book_results": book_results}, timeout=120)
                if resp.status_code != 200:
                    step3_ui.error(f"Provider selection failed ({resp.status_code}): {resp.text}")
                    st.stop()
                best_selections = resp.json()
                st.session_state.best_selections = best_selections
                step3_ui.success("✅ Step 3/4: Determined the best match for each required textbook.")

                step4_ui.info("⏳ Step 4/4: Finalizing rental period results...")
                resp = requests.post(f"{API_BASE}/finalize-results", json={"extraction": extraction, "best_selections": best_selections}, timeout=30)
                if resp.status_code != 200:
                    step4_ui.error(f"Finalization failed ({resp.status_code}): {resp.text}")
                    st.stop()
                final_results = resp.json()
                st.session_state.final_results = final_results
                step4_ui.success("✅ Step 4/4: Complete! View your textbook rental strategy below.")

        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Could not reach the backend. Make sure your FastAPI server is running on port 8001!")

# ---------- Display Results ----------
if st.session_state.final_results:
    extraction = st.session_state.extraction
    final_results = st.session_state.final_results
    books = extraction.get("books", [])
    schedule_items = extraction.get("schedule_items", [])

    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    st.markdown('<p class="center-text main-title" style="font-size: 2.5rem !important;">Your Optimized Strategy</p>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Schedule items
    if schedule_items:
        with st.expander("View Full Course Timeline", expanded=False):
            timeline_rows = [
                {
                    "Type": item.get("item_type", ""),
                    "Label": item.get("label", ""),
                    "Date Text": item.get("date_text", ""),
                    "Start": item.get("start_date", ""),
                    "End": item.get("end_date", ""),
                }
                for item in schedule_items
            ]
            st.dataframe(pd.DataFrame(timeline_rows))

    # Per-book results
    for result in final_results:
        bookname = result.get("bookname", "Unknown")
        author = result.get("author", "")
        best_provider = result.get("best_provider")
        date_periods = result.get("date_periods", [])
        reason = result.get("selection_reason", "")

        st.markdown(f'<div class="section-title" style="border-bottom: 2px solid rgba(120,120,120,0.2); padding-bottom: 8px; margin-top: 2rem;">{escape(bookname)} <span style="font-size: 1.1rem; color: #555; font-weight: 500;">by {escape(author)}</span></div>', unsafe_allow_html=True)

        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.markdown("##### 📅 Active Reading Periods")
            if date_periods:
                for period in date_periods:
                    desc = period.get("description", "")
                    start = period.get("start_date", "")
                    end = period.get("end_date", "")
                    if start and end:
                        st.markdown(f"- **{escape(desc)}**: `{escape(start)}` to `{escape(end)}`")
                    elif desc:
                        st.markdown(f"- **{escape(desc)}**")
            else:
                st.write("No specific dates found. General course duration assumed.")

            if reason:
                st.info(f"💡 **AI Reasoning:** {reason}")

        with col2:
            st.markdown("##### 🛒 Recommended Acquisition")
            if best_provider:
                provider_name = best_provider.get("provider", "Unknown")
                cost = best_provider.get("estimated_cost")
                mode = best_provider.get("acquisition_mode", "")
                link = best_provider.get("provider_link", "")
                price_type = best_provider.get("price_type", mode)

                cost_display = "Free" if cost == 0 else (f"${cost:.2f}" if isinstance(cost, (int, float)) else "N/A")

                st.markdown(
                    f"""
                    <div class="provider-card" style="margin-top: 0;">
                        <div class="provider-topline">
                            <div class="provider-name">{escape(provider_name)}</div>
                            <div class="provider-pill">{escape(mode)}</div>
                        </div>
                        <div class="card-grid">
                            <div class="info-card">
                                <div class="info-card-label">Estimated Cost</div>
                                <div class="info-card-value">{escape(cost_display)}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-card-label">Format</div>
                                <div class="info-card-value">{escape(price_type)}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if link:
                    st.link_button("Open Provider", link, width="stretch")
                else:
                    st.info("Price found, but this provider did not return a direct textbook link.")
            else:
                st.warning("No provider found a match for this book.")

