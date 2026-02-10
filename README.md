# ini-ai

# InI.ai — Interrogate & Illustrate

InI.ai is a learning-focused application designed to help users understand **any topic** by approaching it from two complementary directions:

- **Interrogate** → ask the *right questions*
- **Illustrate** → understand through *clear examples*

The core belief behind InI.ai is simple:

> *Anything in the world can be understood better if we ask relevant questions and see meaningful examples.*

---

## 🚀 What InI.ai Does (v0)

- Accepts a topic from the user
- Generates structured **interrogative questions** about the topic
- Provides **illustrative examples** to ground understanding
- Keeps both modes independent — users can start with either questions or examples

---

## 🧠 Philosophy

Many people struggle not because they are “not smart enough”, but because:
- they don’t know **what questions to ask**
- they don’t get **clear, relatable examples**

InI.ai acts as a **Question Engine** — helping users uncover *what they don’t yet know*.

---

## 🛠 Tech Stack

- **Python**
- **FastAPI** — backend API (Interrogate & Illustrate endpoints)
- **Streamlit** — frontend UI
- **Requests** — frontend ↔ backend communication

All logic is written in Python.

---

## 📁 Project Structure

ini-ai/
├── api/
│ └── main.py # FastAPI backend
└── streamlit_app/
└── app.py # Streamlit frontend






---

## ▶️ How to Run Locally

### 1. Install dependencies
```bash
pip install fastapi uvicorn streamlit requests


start the backend


---

## ▶️ How to Run Locally

### 1. Install dependencies
```bash
pip install fastapi uvicorn streamlit requests



Start the Frontend

python -m streamlit run streamlit_app/app.py


Vision (Future)

InI.ai aims to become a lightweight, intuitive tool for:

learners

career switchers

curious minds

people who learn better through questions + examples


## Windows UTF-8 Note

For clean UTF-8 output when running FastAPI on Windows, set:

```powershell
$env:PYTHONUTF8="1"







Author
Sudipto Bhadra
