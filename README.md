# 🤖 Expert Computer Science FAQ Chatbot

**An intelligent, domain-restricted, offline-capable FAQ assistant designed exclusively for Computer Science students, faculty, and developers.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.3-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📑 Table of Contents
1. [Overview](#-overview)
2. [Key Features](#-key-features)
3. [How the System Works (Architecture)](#-how-the-system-works-architecture)
4. [Technology Stack & Deep Explanation](#-technology-stack--deep-explanation)
5. [Project Structure](#-project-structure)
6. [Installation & Setup](#-installation--setup)
7. [Usage Guide](#-usage-guide)
8. [Data Management](#-data-management)
9. [Roadmap](#-roadmap)
10. [License](#-license)

---

## 🌟 Overview

The **Expert CS FAQ Chatbot** is a specialized conversational AI built to answer questions **exclusively about Computer Science**. 

Unlike general-purpose LLM chatbots (like ChatGPT) that hallucinate, require internet access, and can be tricked into off-topic conversations (like cooking or sports), this bot is:
- **Deterministic**: Answers come from a curated database of 650+ expert FAQs. Zero hallucinations.
- **Domain-Locked**: A custom NLP "Domain Guard" blocks non-CS questions.
- **Lightning Fast**: Sub-50ms response times because all NLP processing happens locally in memory using TF-IDF.
- **100% Offline**: Can be installed as a Progressive Web App (PWA) and works without an internet connection.
- **Private & Free**: No OpenAI API keys, no monthly bills, and no data leaves your server.

### 🎓 Domains Covered
- 🤖 Artificial Intelligence, Machine Learning, Deep Learning, NLP, Computer Vision
- 🔐 Cybersecurity (Attacks, Defenses, Cryptography, AppSec)
- 🌐 Computer Networking (OSI, TCP/IP, DNS, Routing)
- 💻 Programming Languages (Python, Java, C++, JS, Go, Rust)
- 📊 Data Structures & Algorithms
- 🏗️ Software Engineering & Design Patterns
- 🌍 Web Development (Frontend, Backend, APIs)
- 🗄️ Databases (SQL, NoSQL, Redis, MongoDB)
- ⚙️ Operating Systems
- 🧮 Theory of Computation
- ☁️ Cloud & Emerging Tech (Docker, K8s, Blockchain)

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Hybrid Matching Engine** | Combines TF-IDF vectorization, Cosine Similarity, token overlap, and SequenceMatcher fuzzy matching for high accuracy. |
| **Domain Guard** | A custom NLP classifier that checks if a query belongs to Computer Science before searching. |
| **Live Autocomplete** | Real-time typing suggestions with keyboard navigation (↑/↓/Enter) using an in-memory prefix index. |
| **Category Tagging** | Every answer is tagged with its CS subfield (e.g., "Deep Learning"). |
| **User Feedback** | 👍 / 👎 buttons on every answer to track helpfulness. |
| **Unanswered Query Logging** | Every question the bot fails to answer is saved in the DB, helping admins improve the dataset. |
| **Session History** | Conversations are stored per session, so the bot remembers context during a visit. |
| **Bulk Data Import** | Add hundreds of FAQs via a single JSON or CSV file using a Django management command. |
| **Premium UI** | Mobile-first design with glassmorphism effects, custom backgrounds, and typing animations. |
| **PWA Ready** | Installable on mobile home screens and works offline via Service Workers. |

---

## 🧠 How the System Works (Architecture)

The chatbot follows a **Retrieval-Based** architecture. It does **not** use generative AI (like GPT). Instead, it retrieves the best matching answer from a local database using mathematics.

### The Request Pipeline
When a user types a question, the system runs it through **5 distinct steps**:




### 🔬 Step-by-Step Logic Explained

#### 1. Domain Guard (`domain_guard.py`)
Before searching, the bot must verify the question is CS-related. It:
- Normalizes the text (lowercase, removes punctuation).
- Removes stopwords (e.g., "the", "what", "is").
- Compares the remaining tokens against a custom `CS_VOCABULARY` dictionary (containing 1,000+ CS terms across 12 subfields).
- Uses **fuzzy matching** (via `SequenceMatcher`) to catch typos (e.g., "cybersecurty" → "cybersecurity").
- If the confidence score is too low, it returns the polite `REFUSAL_MESSAGE`.

#### 2. TF-IDF Vectorization (`search_engine.py`)
*TF-IDF* stands for **Term Frequency - Inverse Document Frequency**. It converts text into a mathematical vector.
- **Term Frequency (TF)**: How often a word appears in the current FAQ.
- **Inverse Document Frequency (IDF)**: How rare that word is across *all* FAQs.
- **Purpose**: Rare CS terms (like "XGBoost" or "Backpropagation") get a high weight, while common words (like "the" or "difference") get a low weight.

#### 3. Cosine Similarity
Once both the user's query and all FAQs are converted into vectors, we need to find which FAQ is "closest" to the query.
- **Formula**: `cos(θ) = (A · B) / (||A|| ||B||)`
- **Purpose**: Measures the angle between two vectors. A score of `1.0` means identical direction (perfect match). A score of `0.0` means completely unrelated. It ignores the length of the texts, focusing only on their meaning direction in high-dimensional space.

#### 4. Keyword & Fuzzy Boosting
TF-IDF can be fooled by short queries or typos. The engine adds boosts:
- **Exact Substring**: `+0.3` if the query is inside the FAQ.
- **Keyword Overlap**: `+0.25` for every manually-set keyword found.
- **Fuzzy Match**: If the query is short (< 4 words), it runs `SequenceMatcher` (a Ratcliff/Obershelp algorithm) to tolerate typos.
- **Priority Score**: Higher-priority FAQs get a tiny mathematical nudge.

#### 5. Autocomplete (`autocomplete.py`)
Instead of running full TF-IDF on every keystroke (which would be slow), the system builds an **in-memory prefix map**:
- Every word in every FAQ is indexed by its first 3 letters (`pas` → "What is a password?").
- When the user types, it instantly pulls candidates and applies `lru_cache` for O(1) lookups.

---

## 🛠 Technology Stack & Deep Explanation

### Backend Technologies

#### **Python 3.10+**
- **What it is**: A high-level, interpreted programming language.
- **Why we use it**: It is the dominant language in AI/Data Science. It has excellent text processing capabilities and massive library support.

#### **Django 4.2**
- **What it is**: A high-level Python web framework following the Model-View-Template (MVT) pattern.
- **Why we use it**: 
  - **Built-in ORM**: Interact with SQLite without writing raw SQL.
  - **Admin Panel**: Instantly manage FAQs without building a custom dashboard.
  - **Security**: Automatically protects against CSRF, SQL Injection, and XSS.
  - **Scalability**: Handles sessions, routing, and middleware out-of-the-box.

#### **Scikit-Learn**
- **What it is**: The industry-standard Python machine learning library.
- **Why we use it**: We use `TfidfVectorizer` and `cosine_similarity`. Writing these from scratch in pure Python would be extremely slow and error-prone. Scikit-Learn's versions are optimized in C (via NumPy).

#### **NumPy**
- **What it is**: A library for numerical computing in Python.
- **Why we use it**: TF-IDF matrices are massive arrays of numbers. NumPy provides C-level speed for array sorting (`np.argsort`) and mathematical operations, making searches near-instant.

#### **SQLite**
- **What it is**: A lightweight, file-based relational database.
- **Why we use it**: Zero configuration required. Perfect for a self-contained FAQ bot. Easy to migrate to PostgreSQL later if needed.

#### **SequenceMatcher (Python Standard Library)**
- **What it is**: A flexible class from `difflib` that compares sequences.
- **Why we use it**: Implements the **Ratcliff/Obershelp algorithm**, which calculates how similar two strings are based on the longest common subsequences. Used to catch typos so "machne learnin" still finds "machine learning".

### Frontend Technologies

#### **CSS3 (Flexbox + Custom Properties)**
- **What it is**: Stylesheet language with variables and modern layout models.
- **Why we use it**: `:root` variables allow instant theme changes. Flexbox enables smooth chat bubble alignment, and CSS animations handle typing indicators.

#### **PWA (Progressive Web App)**
- **What it is**: A web app that can be installed like a native mobile app.
- **Why we use it**: Uses `manifest.json` (for app icons/name) and `sw.js` (Service Worker for offline caching). Eliminates the need to build a separate Android/iOS app.

---

## 📂 Project Structure

```text
chatbot/                            # Main project root
│
├── manage.py                       # Django entry point
├── db.sqlite3                      # SQLite database (ignored in Git)
├── requirements.txt                # Python dependencies
├── .gitignore                      # Files to exclude from Git
│
├── chatbot/                        # Project settings folder
│   ├── settings.py                 # Django configuration
│   ├── urls.py                     # Root URL routing
│   └── wsgi.py                     # Production server entry point
│
└── chatbot/                        # Main Chatbot App
    ├── models.py                   # Database schema (FAQ, Category, Message)
    ├── views.py                    # API endpoints (ask, suggest, feedback)
    ├── admin.py                    # Django admin customization
    │
    ├── domain_guard.py             # 🧠 CS topic filter and refusal logic
    ├── search_engine.py            # 🧠 TF-IDF & Cosine Similarity algorithm
    ├── autocomplete.py             # 🧠 In-memory prefix index for suggestions
    │
    ├── data/
    │   └── faqs.json               # 📚 650+ curated FAQs
    │
    ├── management/commands/
    │   ├── seed_faqs.py            # Load initial data
    │   └── import_faqs.py          # Bulk loader for JSON/CSV
    │
    ├── templates/chatbot/
    │   └── chat.html               # Main chat interface
    │
    └── static/chatbot/
        ├── css/chat.css            # Styling & animations
        ├── js/chat.js              # Chat logic & fetch API calls
        ├── images/                 # Backgrounds & avatars
