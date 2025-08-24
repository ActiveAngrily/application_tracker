import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import requests
import time

# --- Configuration & Setup ---
st.set_page_config(
    page_title="Automated Application Tracker",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Custom CSS for Styling ---
def load_css():
    """Injects custom CSS for styling the app."""
    st.markdown("""
    <style>
    h1 {
        text-align: center;
        color: #2a2a2a;
    }
    .st-emotion-cache-10trblm { /* Main app container */
        padding: 2rem 3rem;
    }
    .stTextArea textarea {
        min-height: 100px;
        font-size: 1.1rem;
        border-radius: 4px;
        border: 1px solid #ccc;
    }
    .stButton > button {
        border-radius: 4px;
        font-weight: 500;
        padding: 0.75rem 1rem;
        border: 1px solid #aaa;
        background-color: #f0f0f0;
        color: #333;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #e0e0e0;
        border-color: #888;
    }
    .stButton > button:focus {
        box-shadow: 0 0 0 2px white, 0 0 0 4px #aaa;
    }
    .notification-text {
        font-style: italic;
        color: #555;
        text-align: center;
        margin-top: 1rem;
        animation: fadeIn 0.5s ease-in-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .stDataFrame {
        border-radius: 8px;
        max-height: 400px;
        overflow-y: auto;
    }
    .empty-sheet-message {
        text-align: center;
        color: #888;
        font-style: italic;
        padding: 2rem;
        border: 1px dashed #ddd;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Google Sheets & Gemini API Setup ---
@st.cache_resource
def connect_to_gsheet():
    """Connects to the Google Sheet and caches the connection."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        st.info("Please ensure your `secrets.toml` file is correctly configured.")
        return None

@st.cache_data(ttl=30)
def get_sheet_data(_worksheet):
    """Fetches and caches the worksheet data."""
    return _worksheet.get_all_records()

def parse_prompt_with_gemini(prompt):
    """Sends the user's prompt to the Gemini 2.5 Flash API with exponential backoff for rate limiting."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        st.error("GEMINI_API_KEY not found in secrets.toml. Please add it.")
        return None

    # ✅ Updated Model Name for Gemini 2.5 Flash
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    system_prompt = """
    You are a precise data extraction robot. Your only task is to analyze user text and respond with a valid JSON object. Do not add any conversational text or explanations.

    Your JSON output MUST use these exact keys: "action", "company", "job_title", "contact", "status", "notes", "link", "salary", "location", "next_step_date", "recruiter_contact".

    **Rules:**
    - "action": 'CREATE' or 'UPDATE'.
    - "status": Must be one of: 'Applied', 'Assessment', 'Interview Scheduled', 'Offer Received', 'Rejected', 'Followed Up', 'Withdrew'.
    - For any unmentioned field, the value must be an empty string "".

    **Examples:**
    1. User text: 'Just applied for a 'Senior Data Engineer' role at Databricks. Recruiter is Jessica Miller.'
    Correct JSON output: { "action": "CREATE", "company": "Databricks", "job_title": "Senior Data Engineer", "status": "Applied", "recruiter_contact": "Jessica Miller", "contact": "", "notes": "", "link": "", "salary": "", "location": "", "next_step_date": "" }

    2. User text: 'Update on Vercel: interview scheduled for next Tuesday for the Senior Frontend Engineer role.'
    Correct JSON output: { "action": "UPDATE", "company": "Vercel", "job_title": "Senior Frontend Engineer", "status": "Interview Scheduled", "next_step_date": "next Tuesday", "contact": "", "notes": "", "link": "", "salary": "", "location": "", "recruiter_contact": "" }
    """

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"{system_prompt}\n\nUser text: '{prompt}'"}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    retries = 3
    delay = 2

    for i in range(retries):
        try:
            response = requests.post(api_url, json=payload, timeout=60)
            response.raise_for_status()
            response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(response_text)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 429:
                st.warning(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
            else:
                st.error(f"API Request Error: An HTTP error occurred: {err}")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"API Request Error: Could not connect. {e}")
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            st.error(f"API Response Error: Failed to parse the AI's response. {e}")
            return None

    st.error("API rate limit still exceeded. Please wait a minute before trying again.")
    return None

# --- Main Application Logic ---
def main():
    load_css()
    st.title("Automated Application Tracker")

    main_col1, main_col2, main_col3 = st.columns([1, 2, 1])
    with main_col2:
        prompt = st.text_area("Enter your update here...", placeholder="e.g., Applied to Vercel for the frontend engineer role...", label_visibility="collapsed")
        update_button = st.button("Update", use_container_width=True)
        status_container = st.empty()

    client = connect_to_gsheet()
    if not client: return

    try:
        GSHEET_NAME = st.secrets["GSHEET_NAME"]
        spreadsheet = client.open(GSHEET_NAME)
        worksheet = spreadsheet.worksheet("Applications")
    except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        status_container.error(f"Error: {e}. Please check your sheet and worksheet names.")
        return
    except Exception as e:
        status_container.error(f"An error occurred while opening the sheet: {e}")
        return

    try:
        headers = worksheet.row_values(1)
        if not headers or not any(h.strip() for h in headers):
            status_container.error("Your Google Sheet has no header row. Please add column names in the first row.")
            return
    except Exception as e:
        status_container.error(f"Could not read the header row from your sheet: {e}")
        return

    if update_button and prompt:
        with st.spinner("AI is analyzing your input..."):
            parsed_data = parse_prompt_with_gemini(prompt)

        if parsed_data:
            company = (parsed_data.get("company", "") or parsed_data.get("company_name", "")).strip()
            action = parsed_data.get("action", "").upper()

            if not company:
                status_container.error("AI could not identify a company name. Please be more specific.")
            else:
                try:
                    with st.spinner(f"Updating your spreadsheet for {company}..."):

                        json_to_header_map = {
                            "company": "Company", "job_title": "Job Title", "contact": "Contact", "status": "Status",
                            "notes": "Notes", "link": "Link to Application", "salary": "Salary", "location": "Location",
                            "next_step_date": "Next Step Date", "recruiter_contact": "Recruiter Contact"
                        }

                        if 'Company' not in headers:
                            status_container.error("Your sheet must have a 'Company' column to work correctly.")
                            return

                        company_col_index = headers.index('Company') + 1
                        cell_list = worksheet.findall(company, in_column=company_col_index, case_sensitive=False)

                        if action == "CREATE" and not cell_list:
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            new_row_dict = {h: '' for h in headers}

                            for json_key, header_name in json_to_header_map.items():
                                if header_name in new_row_dict:
                                    new_row_dict[header_name] = parsed_data.get(json_key, "")

                            if "Date Applied" in new_row_dict: new_row_dict["Date Applied"] = now.split(" ")[0]
                            if "Last Updated" in new_row_dict: new_row_dict["Last Updated"] = now

                            # Build the list in the correct order based on headers
                            final_row_values = [new_row_dict.get(h, '') for h in headers]
                            worksheet.append_row(final_row_values)
                            status_container.success(f"Successfully added **{company}** to your sheet!")

                        elif action == "UPDATE" or cell_list:
                            if not cell_list:
                                status_container.warning(f"Could not find **{company}** to update.")
                            else:
                                target_row_index = cell_list[0].row
                                cells_to_update = []
                                for header_name in headers:
                                    # Find the corresponding json key for this header
                                    json_key = next((k for k, v in json_to_header_map.items() if v == header_name), None)
                                    if json_key and parsed_data.get(json_key):
                                        col_index = headers.index(header_name) + 1
                                        cells_to_update.append(gspread.Cell(target_row_index, col_index, value=parsed_data[json_key]))

                                if "Last Updated" in headers:
                                    col_index = headers.index("Last Updated") + 1
                                    cells_to_update.append(gspread.Cell(target_row_index, col_index, value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                                if cells_to_update:
                                    worksheet.update_cells(cells_to_update)
                                    status_container.success(f"Successfully updated **{company}** in your sheet!")
                                else:
                                    status_container.info("No new information was found to update.")
                        else:
                            status_container.error(f"Could not determine whether to create or update for {company}.")

                    st.cache_data.clear()

                except Exception as e:
                    status_container.error(f"An error occurred while updating the sheet: {e}")

        time.sleep(3)
        status_container.empty()

    elif update_button and not prompt:
        status_container.warning("Please enter an update.")

    st.markdown("---")
    st.subheader("Dashboard")
    try:
        data = get_sheet_data(worksheet)
        if data:
            df = pd.DataFrame(data)
            # Ensure dataframe columns match the header order from the sheet
            st.dataframe(df[headers], use_container_width=True)
        else:
            st.markdown("<p class='empty-sheet-message'>Your sheet is currently empty.</p>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Could not fetch data from the sheet. {e}")

if __name__ == "__main__":
    main()
