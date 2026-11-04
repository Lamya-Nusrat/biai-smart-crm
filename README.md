
# BIAI SmartCRM

An AI-powered customer enquiry management application developed for the BIAI AI Intern Round 2 assessment (Task 1).

## Overview

BIAI SmartCRM helps organize customer enquiries received through WhatsApp, Facebook, websites, and phone calls.

The application uses Google Gemini AI to extract customer information from pasted enquiries and suggest replies in English or Banglish.

## Features

- AI-powered extraction of customer name, phone number, source, programme, and language
- Suggested customer replies in English or Banglish
- Review and edit extracted information before saving
- Save enquiries using SQLite
- Search, view, edit, and delete saved enquiries
- Update enquiry status
- Track enquiries across New, Contacted, Interested, Paid, and Lost
- Dashboard showing enquiry counts and pipeline overview

## Technologies

- Python
- Streamlit
- Google Gemini API
- SQLite
- Pandas

## Installation

1. Clone or download this repository.
2. Install the required packages:

```bash
python -m pip install -r requirements.txt
```

3. Create a file named `.streamlit/secrets.toml` and add your own Gemini API key:

```toml
GEMINI_API_KEY = "YOUR_API_KEY"
```

4. Run the application:

```bash
python -m streamlit run app.py
```

## Sample Data

The project uses fictional sample enquiries provided by BIAI for its Round 2 assessment. No real customer data is used.

## Current Limitations

- AI-generated replies may require human review, particularly for Banglish.
- Gemini API availability depends on external service availability and quota.
- SQLite data is stored locally; persistent storage for cloud deployment requires additional setup.
- Automated follow-up reminders are not implemented.

## Gemini Free Tier Limitations

This application uses the Google Gemini API Free Tier, which has usage limits, including requests per minute and requests per day.

When the quota is exceeded, AI information extraction and suggested reply generation may become temporarily unavailable. For example, the API may return a `429 RESOURCE_EXHAUSTED` error.

The application displays a user-friendly error message instead of technical API details.

Gemini model fallback helps with certain temporary service errors but does not guarantee uninterrupted availability.

Users can check their API usage and limits through Google AI Studio:
https://aistudio.google.com/rate-limit

The application can be used within the available free quota without enabling paid billing.

## Future Improvements

- Follow-up reminders
- Improved Banglish reply evaluation
- Persistent cloud database
- Weekly AI-generated enquiry summary

## Project Context

Created for BIAI AI Intern Round 2 — Task 1: BIAI CRM.