# 📖 Example Usage Flows: Rent Smart

This app is designed to help students save money on textbooks by only renting them for the specific weeks they are actually needed in a course.

---

## 🏗️ Scenario 1: The "Optimization" Flow
**Goal:** Find out exactly when you need to rent your books and where to get them for the cheapest price.

1.  **Launch the App**: Run the FastAPI backend and then the Streamlit frontend.
2.  **Upload Syllabus**: Drag and drop your course syllabus (e.g., `CS101_Syllabus.pdf`) into the "DRAG/DROP" area.
3.  **Set Your Profile**:
    *   **Known Topics**: "I already know basic Python loops and variables."
    *   **Budget**: "Under $50."
    *   **Format**: "Digital only preferred."
4.  **Analyze**: Click **"Analyze Syllabus"**.
5.  **View "Recommended Access Periods"**:
    *   The AI might find that you only need a specific $100 textbook for **Weeks 4 to 8**.
    *   It will recommend a **30-day rental** starting on your Week 4 date rather than buying the whole book for the semester.
6.  **Acquire**: Click the **"Open Best Provider"** button to go directly to the cheapest identified store.

---

## 💬 Scenario 2: The "Smart Study" Chat Flow
**Goal:** Get a personalized plan on what to study based on your current knowledge.

1.  **Complete Analysis**: (Same as above).
2.  **Open Chat**: Use the **"Study Strategy Chat"** in the bottom right.
3.  **Ask a Question**:
    *   *"Given I already know Python basics, which chapters in 'Python for Data Science' can I skip?"*
    *   *"I'm on a tight budget. If I can only afford one book this month, which one is more critical based on the upcoming exam?"*
4.  **Receive Strategy**: The AI uses the syllabus timeline and your profile to tell you exactly which weeks you can afford to hold off on renting specific books.

---

## 📉 Scenario 3: The "Deep Price Check" Flow
**Goal:** Manually check availability for a specific book.

If you don't want to upload a full syllabus, you can use the API directly (or see the aggregation logic):
1.  **Call `/search_books?q=Organic Chemistry`**: Get a list of potential ISBNs.
2.  **Call `/compare_book_providers`**: The system will automatically check:
    *   **eCampus**: For physical/digital rental prices.
    *   **Open Library**: For free digital borrowing.
    *   **Google Books**: For previews and ebook prices.
    *   **Internet Archive**: For free historical copies.
3.  **Decision**: The system returns the provider with the lowest cost and a direct link.
