import pandas as pd
import requests
import streamlit as st
from html import escape

st.set_page_config(page_title="Rent Smart", layout="centered")

if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "planner_messages" not in st.session_state:
    st.session_state.planner_messages = []

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
    .section-copy {
        color: #000000;
    }
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
    .profile-shell {
        border: 2px solid #000000;
        border-radius: 22px;
        padding: 0.9rem 1rem;
        background: rgba(255, 255, 255, 0.18);
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
    .chat-shell .section-title {
        margin-top: 0;
        font-size: 1.15rem;
    }
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
    .chat-content p {
        margin: 0;
        color: #000000;
    }
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
        .chat-scroll {
            max-height: 300px;
        }
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
    [data-testid="stFileUploader"] * {
        color: #000000 !important;
    }
    [data-testid="stFileUploaderFile"] *,
    [data-testid="stFileUploaderDropzone"] * {
        color: #000000 !important;
    }
    [data-testid="stBaseButton-secondary"] {
        color: #ffffff !important;
    }
    [data-testid="stBaseButton-secondary"] * {
        color: #ffffff !important;
    }
    .chat-shell textarea,
    .chat-shell textarea:focus {
        background: #ffffff !important;
        color: #000000 !important;
    }
    label, .stTextArea label, .stTextInput label, .stSelectbox label {
        color: #000000 !important;
    }
    [data-testid="stWidgetLabel"] * {
        color: #000000 !important;
    }
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
    [data-testid="stExpander"] * {
        color: #000000 !important;
    }
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] details > div {
        background: rgba(255, 255, 255, 0.74) !important;
    }
</style>
""", unsafe_allow_html=True)

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

uploaded_file = st.file_uploader("DRAG/DROP YOUR FILES HERE", type=["pdf"], label_visibility="hidden")

st.markdown('<div class="profile-box">', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown('<div class="section-title">Student Profile</div>', unsafe_allow_html=True)
    known_topics = st.text_area(
        "What topics do you already know?",
        placeholder="Example: limits, derivatives, cell biology basics, microeconomics fundamentals.",
    )
    budget = st.text_input(
        "What is your budget?",
        placeholder="Example: under $40 or cheapest possible.",
    )
    textbook_format_preference = st.selectbox(
        "Preferred textbook format",
        options=["No preference", "Digital only", "Physical only", "Borrow/open access preferred"],
    )
    exam_date_flexibility = st.selectbox(
        "Are exam dates fixed or flexible?",
        options=["Fixed", "Mostly fixed", "Somewhat flexible", "Very flexible"],
    )
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file is not None:
    if st.button("Analyze Syllabus", use_container_width=True, type="primary"):
        with st.spinner("Extracting textbooks, schedule, and chapter focus from syllabus..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                response = requests.post("http://localhost:8000/analyze-syllabus", files=files)

                if response.status_code == 200:
                    analysis = response.json()
                    st.session_state.analysis = analysis
                    st.session_state.planner_messages = [
                        {
                            "role": "assistant",
                            "content": (
                                "I have your syllabus analysis, including textbooks, schedule, and chapter focus. "
                                "Use the Student Profile window above to set your budget, preferred format, and date flexibility, "
                                "then ask what to study, what can be skipped, or which access strategy is cheapest."
                            ),
                        }
                    ]

                    books = analysis.get("books", [])
                    book_chapters = analysis.get("book_chapters", [])
                    schedule_items = analysis.get("schedule_items", [])
                    rental_recommendations = analysis.get("rental_recommendations", [])
                    course_calendar_context = analysis.get("course_calendar_context", {})

                    st.success("Analysis Complete!")

                    if books:
                        st.markdown('<div class="section-title">Required Textbooks Found</div>', unsafe_allow_html=True)
                        st.dataframe(pd.DataFrame(books), use_container_width=True)

                        st.markdown('<div class="section-title">Chapter Map</div>', unsafe_allow_html=True)
                        if book_chapters:
                            for chapter_plan in book_chapters:
                                with st.expander(f"Chapter focus for: {chapter_plan.get('bookname', 'Unknown')}", expanded=False):
                                    chapter_focuses = chapter_plan.get("chapter_focuses", [])
                                    topic_focuses = chapter_plan.get("topic_focuses", [])
                                    if chapter_focuses:
                                        st.markdown('<div class="section-copy"><strong>Likely chapters or sections:</strong></div>', unsafe_allow_html=True)
                                        for chapter in chapter_focuses:
                                            st.markdown(f'<div class="section-copy">- {chapter}</div>', unsafe_allow_html=True)
                                    if topic_focuses:
                                        st.markdown('<div class="section-copy"><strong>Likely topic focus:</strong></div>', unsafe_allow_html=True)
                                        for topic in topic_focuses:
                                            st.markdown(f'<div class="section-copy">- {topic}</div>', unsafe_allow_html=True)
                                    if chapter_plan.get("notes"):
                                        st.markdown(f'<div class="section-copy">{chapter_plan.get("notes")}</div>', unsafe_allow_html=True)
                        else:
                            st.info("No chapter map was extracted from this syllabus.")

                        st.markdown('<div class="section-title">Course Timeline</div>', unsafe_allow_html=True)
                        if schedule_items:
                            timeline_rows = [
                                {
                                    "Type": item.get("item_type"),
                                    "Label": item.get("label"),
                                    "Raw Date": item.get("raw_date_text"),
                                    "Start": item.get("start_date"),
                                    "End": item.get("end_date"),
                                    "Week": item.get("week_label"),
                                    "Estimated": item.get("is_estimated"),
                                }
                                for item in schedule_items
                            ]
                            st.dataframe(pd.DataFrame(timeline_rows), use_container_width=True)
                        else:
                            st.info("No dated schedule items were extracted from this syllabus.")

                        if course_calendar_context:
                            st.markdown('<div class="section-title">Calendar Context</div>', unsafe_allow_html=True)
                            anchor_notes = course_calendar_context.get("date_anchor_notes", [])
                            st.markdown(
                                f"""
                                <div class="card-grid">
                                    <div class="info-card">
                                        <div class="info-card-label">Term</div>
                                        <div class="info-card-value">{course_calendar_context.get("term_label") or "Not detected"}</div>
                                    </div>
                                    <div class="info-card">
                                        <div class="info-card-label">Course Start</div>
                                        <div class="info-card-value">{course_calendar_context.get("course_start_date") or "Unknown"}</div>
                                    </div>
                                    <div class="info-card">
                                        <div class="info-card-label">Course End</div>
                                        <div class="info-card-value">{course_calendar_context.get("course_end_date") or "Unknown"}</div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            if anchor_notes:
                                notes_html = "".join(
                                    f'<div class="info-card" style="margin-bottom: 0.55rem;"><div class="info-card-value" style="font-size:0.92rem; font-weight:600;">{note}</div></div>'
                                    for note in anchor_notes
                                )
                                st.markdown(notes_html, unsafe_allow_html=True)

                        st.markdown('<div class="section-title">Recommended Access Periods</div>', unsafe_allow_html=True)
                        for recommendation in rental_recommendations:
                            book = recommendation.get("book", {})
                            periods = recommendation.get("periods", [])
                            pricing_recommendation = recommendation.get("pricing_recommendation", {})
                            title = book.get("bookname", "Unknown")

                            with st.expander(f"Optimization for: {title}", expanded=True):
                                if periods:
                                    st.write("Recommended access periods:")
                                    for period in periods:
                                        period_label = f"- {period.get('start_date')} to {period.get('end_date')}"
                                        if period.get("is_estimated"):
                                            period_label += " (estimated)"
                                        st.write(period_label)
                                        st.caption(period.get("rental_reasoning", ""))

                                    first_period = periods[0]
                                    col1, col2 = st.columns(2)
                                    col1.metric(label="Recommended Periods", value=str(len(periods)))
                                    col2.metric(
                                        label="First Access Window",
                                        value=f"{first_period.get('start_date')} to {first_period.get('end_date')}",
                                    )
                                else:
                                    st.info("No reliable access window could be inferred for this book.")

                                if pricing_recommendation:
                                    st.write("### Best Price Recommendation")
                                    st.write(f"Action: {pricing_recommendation.get('recommended_action') or 'Unavailable'}")
                                    st.write(f"Recommended duration: {pricing_recommendation.get('recommended_duration_days', 0)} day(s)")
                                    st.caption(pricing_recommendation.get("recommendation_reason", ""))
                                    if pricing_recommendation.get("edition_warning"):
                                        st.warning(pricing_recommendation.get("edition_warning"))

                                    best_provider = pricing_recommendation.get("best_provider")
                                    if best_provider:
                                        st.markdown(
                                            f"""
                                            <div class="provider-card">
                                                <div class="provider-topline">
                                                    <div class="provider-name">{best_provider.get("provider", "Unknown provider")}</div>
                                                    <div class="provider-pill">{best_provider.get("acquisition_mode", "unavailable")}</div>
                                                </div>
                                                <div class="card-grid">
                                                    <div class="info-card">
                                                        <div class="info-card-label">Estimated Cost</div>
                                                        <div class="info-card-value">{best_provider.get("estimated_cost", "N/A")}</div>
                                                    </div>
                                                    <div class="info-card">
                                                        <div class="info-card-label">Format</div>
                                                        <div class="info-card-value">{best_provider.get("price_type", best_provider.get("acquisition_mode", "N/A"))}</div>
                                                    </div>
                                                </div>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )
                                        if best_provider.get("provider_link"):
                                            st.link_button("Open Best Provider", best_provider.get("provider_link"), use_container_width=True)
                                        else:
                                            st.info("Price found, but this provider did not return a direct textbook link.")
                    else:
                        st.warning("No textbooks were detected in this syllabus.")
                else:
                    st.error(f"Backend Error ({response.status_code}): {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("Connection Error: Could not reach the backend. Make sure your FastAPI server is running on port 8000!")

st.markdown("<br><br>", unsafe_allow_html=True)
chat_left, chat_right = st.columns([3.2, 1.35])
with chat_right:
    st.markdown("<br><br>", unsafe_allow_html=True)

# We wrap the entire chat interface in a container that your CSS targets via the .chat-panel class
st.markdown('<div class="chat-panel">', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown('<div class="section-title">Study Strategy Chat</div>', unsafe_allow_html=True)

    # Render the chat history
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for message in st.session_state.planner_messages:
        role = message.get("role", "assistant")
        role_label = "You" if role == "user" else "SmartRent AI"
        st.markdown(
            f"""
            <div class="chat-bubble {escape(role)}">
                <div class="chat-role">{escape(role_label)}</div>
                <div class="chat-content">{escape(message.get("content", ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # Use a Streamlit form for the chat input so hitting "Enter" or "Send" triggers the submission cleanly
    st.markdown('<div class="chat-input-shell">', unsafe_allow_html=True)
    with st.form(key="chat_form", clear_on_submit=True):
        user_chat = st.text_area(
            "Ask SmartRent AI",
            placeholder="Ask about what to study, what can be skipped, or the best buy/rent strategy...",
            label_visibility="collapsed",
            height=90,
        )
        send_chat = st.form_submit_button("Send", use_container_width=True, type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # Close chat-panel

# Handle the chat submission logic
if send_chat and user_chat.strip():
    # 1. Immediately append user message to history
    st.session_state.planner_messages.append({"role": "user", "content": user_chat})

    # 2. Check if analysis exists
    if not st.session_state.analysis:
        st.session_state.planner_messages.append(
            {
                "role": "assistant",
                "content": "Upload and analyze a syllabus first so I can build a study and textbook access plan.",
            }
        )
    else:
        # 3. Call backend
        try:
            payload = {
                "analysis": st.session_state.analysis,
                "user_context": {
                    "known_topics": known_topics,
                    "budget": budget,
                    "textbook_format_preference": textbook_format_preference,
                    "exam_date_flexibility": exam_date_flexibility,
                },
                "user_message": user_chat,
                "chat_history": st.session_state.planner_messages[:-1], # Exclude the current message we just added
            }
            response = requests.post("http://localhost:8000/chat-study-plan", json=payload)

            if response.status_code == 200:
                assistant_message = response.json().get("assistant_message", "I couldn't generate a study plan just now.")
            else:
                assistant_message = f"Backend Error ({response.status_code}): {response.text}"
        except requests.exceptions.ConnectionError:
            assistant_message = "Connection Error: Could not reach the backend. Make sure your FastAPI server is running on port 8000!"

        # 4. Append AI response to history
        st.session_state.planner_messages.append({"role": "assistant", "content": assistant_message})
    
    # 5. Rerun to update the UI with the new messages
    st.rerun()