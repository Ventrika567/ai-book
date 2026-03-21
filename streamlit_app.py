import json
import os
import tempfile

import streamlit as st

from app import call_openai_for_json, extract_text_from_pdf


st.set_page_config(page_title="PDF Book Extractor", page_icon="Books", layout="wide")

st.title("PDF Book Extractor")
st.write("Upload a PDF and extract the books mentioned in it as JSON.")

uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    if st.button("Extract books", type="primary"):
        with st.spinner("Reading PDF and extracting books..."):
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                    temp_file.write(uploaded_file.getvalue())
                    temp_path = temp_file.name

                extracted_text = extract_text_from_pdf(temp_path)
                if not extracted_text.strip():
                    st.error("Could not extract text from the PDF. It may be scanned or empty.")
                else:
                    books = call_openai_for_json(extracted_text)
                    st.success(f"Extracted {len(books)} book(s).")
                    st.json(books)
                    st.download_button(
                        "Download JSON",
                        data=json.dumps(books, indent=2),
                        file_name=f"{os.path.splitext(uploaded_file.name)[0]}_books.json",
                        mime="application/json",
                    )
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
            finally:
                if temp_path:
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
