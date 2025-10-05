# 🤖 AI Personal Email Automator

An intelligent email assistant that **classifies your inbox** and **drafts smart replies** — all powered by Python, Gmail API, and optional AI enhancement.

[![Demo Video](https://www.loom.com/share/fc14056d72a64d50aff748517cb48411)


> _“Finally, an email assistant that respects my time — not just another spam filter.”_

---

## ✨ Features

- **Smart Classification**: Automatically sorts emails into:
  - `Urgent` (deadlines, priority contacts)
  - `Work` (professional, non-urgent)
  - `Social` (friends, family)
  - `Spam` (promotional, irrelevant)
- **Custom Rules**: Mark senders like `boss@company.com` as urgent
- **AI-Powered Replies**: Optional OpenAI integration for natural-language responses
- **Rule-Based Fallback**: Works even without an API key
- **Gmail Integration**: Read, classify, and **send replies directly**
- **Privacy-First**: No data leaves your machine

---

## 🚀 Live Demo

Try it yourself on **Streamlit Cloud** (coming soon!)  
👉 [Watch the 60-second demo](https://www.loom.com/share/fc14056d72a64d50aff748517cb48411)

---

## 🛠️ Run Locally

### Prerequisites
- Python 3.8+
- [Gmail API credentials](#gmail-api-setup) (`credentials.json`)
- (Optional) [OpenAI API key](https://platform.openai.com/api-keys)

### Setup
1. Clone this repo:
   ```bash
   git clone https://github.com/drbetique/ai-email-automator.git
   cd ai-email-automator