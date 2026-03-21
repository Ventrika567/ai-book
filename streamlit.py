import streamlit as st
import requests
import pandas as pd

# 1. Setup Page & Theme
st.set_page_config(page_title="Rent Smart", layout="centered")

# Custom CSS to mimic your mockup's purple theme and typography
st.markdown("""
<style>
    /* Light purple background */
    .stApp {
        background-color: #C0C0C0; 
    }
    /* Centered Text */
    .center-text {
        text-align: center;
        color: #000000;
        font-family: sans-serif;
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
    .uploader-title {
        text-align: center;
        font-weight: 800;
        font-size: 1.25rem;
        color: #2e2250;
        letter-spacing: 0.03em;
        margin-bottom: 0.6rem;
    }
    .uploader-subtitle {
        text-align: center;
        font-size: 0.95rem;
        color: #5b4f7f;
        margin-bottom: 1rem;
    }
    /* Style the file uploader box to look more like a modern dropzone */
    [data-testid="stFileUploader"] {
        color: #000000;
        max-width: 760px;
        margin: 0 auto 0.5rem auto;
    }
    [data-testid="stFileUploader"] section {
        color: #000000;
        border-radius: 22px;
        border: 2px dashed #000000;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.68) 0%, rgba(237, 228, 255, 0.85) 100%);
        box-shadow: 0 12px 30px rgba(74, 54, 124, 0.12);
        padding: 0.5rem 0.85rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: #000000;
        box-shadow: 0 16px 36px rgba(74, 54, 124, 0.2);
        transform: translateY(-1px);
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        color: #000000 !important;
        font-weight: 600;
    }
    [data-testid="stFileUploaderDropzone"] small {
        color: #000000 !important;
    }
    [data-testid="stFileUploaderDropzone"] * {
        color: #000000 !important;
    }
    [data-testid="stBaseButton-secondary"] {
        border-radius: 999px !important;
        border: 1px solid #bcaee8 !important;
        background: #ffffff !important;
        color: #35295a !important;
        font-weight: 700 !important;
        padding: 0.35rem 1.2rem !important;
    }
    [data-testid="stBaseButton-secondary"]:hover {
        border-color: #9883dd !important;
        color: #2f2450 !important;
    }
    /* Micro-Rental Optimization result boxes (st.expander) */
    [data-testid="stExpander"] {
        background-color: #4a4a4a !important;
        border: 1px solid #3f3f3f !important;
    }
    [data-testid="stExpander"] details {
        background-color: #4a4a4a !important;
    }
    [data-testid="stExpander"] details > div {
        background-color: #4a4a4a !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. Header Section
st.markdown('<p class="center-text sub-title">RENT SMART - PAY LESS</p>', unsafe_allow_html=True)
st.markdown('<p class="center-text main-title">Your Optimized Textbook Rental Engine</p>', unsafe_allow_html=True)
st.markdown('<p class="center-text description">Upload your syllabus and let our AI calculate your active reading dates to find the cheapest micro-rental.<br><b>You only pay</b> for the time you need!</p>', unsafe_allow_html=True)

# 3. File Uploader Area
uploaded_file = st.file_uploader("DRAG/DROP YOUR FILES HERE", type=["pdf"], label_visibility="hidden")

# 4. Processing Logic
if uploaded_file is not None:
    # Adding an analyze button to match your UI flow
    if st.button("Analyze Syllabus", use_container_width=True, type="primary"):
        with st.spinner("Extracting textbook requirements from syllabus..."):
            try:
                # Prepare the file for the FastAPI endpoint
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                
                # Make the request to your backend
                response = requests.post("http://localhost:8000/parse-pdf", files=files)

                if response.status_code == 200:
                    books = response.json()
                    st.success("Analysis Complete!")

                    if books:
                        st.write("### 📚 Required Textbooks Found")
                        # Display books nicely in a dataframe
                        df = pd.DataFrame(books)
                        st.dataframe(df, use_container_width=True)

                        # --- HACKATHON MENTOR MAGIC ---
                        # Your backend currently extracts *which* books are needed. 
                        # To sell the vision, we will simulate the cost savings UI here!
                        st.write("### 💸 Micro-Rental Optimization")
                        for book in books:
                            with st.expander(f"Optimization for: {book.get('bookname', 'Unknown')}", expanded=True):
                                col1, col2 = st.columns(2)
                                col1.metric(label="Standard 180-Day Rental", value="$80.00")
                                col2.metric(label="Calculated 21-Day Micro-Rental", value="$14.50", delta="-$65.50 Saved", delta_color="inverse")
                                st.write("**Active Reading Window:** Weeks 3 - 5")
                                st.button(f"Rent '{book.get('bookname')}' for $14.50", key=book.get('bookname'))
                    else:
                        st.warning("No textbooks were detected in this syllabus.")
                else:
                    st.error(f"Backend Error ({response.status_code}): {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("🚨 Connection Error: Could not reach the backend. Make sure your FastAPI server is running on port 8000!")

# 5. Bottom Chat Input (To match your UI mockup)
st.markdown("<br><br>", unsafe_allow_html=True)
user_chat = st.chat_input("Drop syllabus above or start a conversation...")
if user_chat:
    st.info(f"Chat functionality coming soon! You said: {user_chat}")
