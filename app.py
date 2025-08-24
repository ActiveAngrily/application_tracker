import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import requests # Using requests for the Gemini API call

# --- Configuration & Setup ---

# Set page configuration
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

            /* --- Widget Styling --- */
            .st-emotion-cache-10trblm { /* Main app container */
                padding: 2rem 3rem;
            }

            /* Make the text area larger */
            .stTextArea textarea {
                min-height: 100px; /* Set a minimum height for multiple lines */
                font-size: 1.1rem;
                border-radius: 4px; /* Sharper corners for classic look */
                border: 1px solid #ccc;
            }

            /* --- Classic Button Styling --- */
            .stButton > button {
                border-radius: 4px;
                font-weight: 500;
                padding: 0.75rem 1rem;
                border: 1px solid #aaa;
                background-color: #f0f0f0; /* Light grey background */
                color: #333;
                transition: all 0.2s ease-in-out;
            }
            
            .stButton > button:hover {
                background-color: #e0e0e0;
                border-color: #888;
            }
            
            .stButton > button:focus {
                box-shadow: 0 0 0 2px white, 0 0 0 4px #aaa; /* Classic focus ring */
            }

            /* --- Custom Text Notification Styling --- */
            .notification-text {
                font-style: italic;
                color: #555;
                text-align: center;
                margin-top: 1rem;
            }
            
            /* --- Dataframe Styling --- */
            .stDataFrame {
                border-radius: 8px;
                max-height: 300px; /* Set max height for approx 4-5 rows */
                overflow-y: auto; /* Enable vertical scrolling */
            }
            
            /* --- Custom Styling for Empty Sheet Message --- */
            .empty-sheet-message {
                text-align: center;
                color: #888; /* Light grey text */
                font-style: italic;
                padding: 2rem;
                border: 1px dashed #ddd; /* Dashed border */
                border-radius: 8px;
            }

        </style>
    """, unsafe_allow_html=True)


# --- Google Sheets & Gemini API Setup ---

# Function to connect to Google Sheets
def connect_to_gsheet():
    """
    Connects to the Google Sheet using credentials stored in Streamlit Secrets.
    """
    try:
        # Scopes for the Google Sheets and Drive APIs
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        st.info("Please ensure your `secrets.toml` file is correctly configured with your Google Cloud service account credentials.")
        return None

# Function to call Gemini API for Natural Language Processing
def parse_prompt_with_gemini(prompt):
    """
    Sends the user's prompt to the Gemini API to extract structured data.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        st.error("GEMINI_API_KEY not found in secrets.toml. Please add it.")
        return None
        
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

    # The detailed instruction for the model
    system_prompt = """
    You are an intelligent assistant for a job application tracker. 
    Your task is to extract structured information from the user's text and respond ONLY with a valid JSON object.
    Use the following keys in your JSON response: "action", "company", "job_title", "contact", "status", "notes", "link", "salary", "location", "next_step_date", "recruiter_contact".

    - Analyze the text to determine if it's a new application ('CREATE') or an update to an existing one ('UPDATE') for the "action" key.
    - Extract the company name for the "company" key.
    - Extract the job title for the "job_title" key.
    - Extract the contact (email or platform like LinkedIn) for the "contact" key.
    - Extract the application status for the "status" key. Use one of these predefined categories: 'Applied', 'Assessment', 'Interview Scheduled', 'Offer Received', 'Rejected', 'Followed Up', 'Withdrew'.
    - Extract any other relevant information as "notes".
    - Extract any URLs for the "link" key.
    - Extract salary information for the "salary" key.
    - Extract the location (e.g., Remote, Hybrid, City) for the "location" key.
    - Extract any dates for future events for the "next_step_date" key.
    - Extract any recruiter names or contacts for the "recruiter_contact" key.
    - If a field isn't mentioned, set its value to an empty string "".
    """

    # Construct the payload for the API
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\nUser text: '{prompt}'"}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
        }
    }

    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        
        # The API returns the JSON as a string in the 'text' field
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        return json.loads(response_text)

    except requests.exceptions.RequestException as e:
        st.error(f"API Request Error: Could not connect to the Gemini API. {e}")
        return None
    except (KeyError, IndexError) as e:
        st.error(f"API Response Error: The response from the AI was not in the expected format. {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"API JSON Error: Failed to parse the AI's response. {e}")
        st.write("Raw AI Response:", response.text) # Show raw response for debugging
        return None


# --- Main Application Logic ---

def main():
    load_css() # Apply the custom styles

    st.title("Automated Application Tracker")
    
    # --- Centered Main Content ---
    main_col1, main_col2, main_col3 = st.columns([1, 2, 1])
    with main_col2:
        # --- User Input (Centered and Larger) ---
        prompt = st.text_area("Enter your update here...", placeholder="e.g., Applied to Vercel for the frontend engineer role...", label_visibility="collapsed")
        update_button = st.button("Update", use_container_width=True)
        # Placeholder for notifications
        notification_placeholder = st.empty()

    # Connect to Google Sheets
    client = connect_to_gsheet()

    if client:
        try:
            GSHEET_NAME = st.secrets["GSHEET_NAME"]
            spreadsheet = client.open(GSHEET_NAME)
            worksheet = spreadsheet.worksheet("Applications")
        except gspread.exceptions.SpreadsheetNotFound:
            notification_placeholder.markdown(f"<p class='notification-text' style='color: #D8000C;'>Spreadsheet named '{st.secrets.get('GSHEET_NAME', 'GSHEET_NAME_not_found')}' not found.</p>", unsafe_allow_html=True)
            return
        except gspread.exceptions.WorksheetNotFound:
            notification_placeholder.markdown("<p class='notification-text' style='color: #D8000C;'>Worksheet named 'Applications' not found.</p>", unsafe_allow_html=True)
            return
        except Exception as e:
            notification_placeholder.markdown(f"<p class='notification-text' style='color: #D8000C;'>An error occurred while opening the sheet: {e}</p>", unsafe_allow_html=True)
            return

        if update_button:
            if prompt:
                with st.spinner("AI is processing your request..."):
                    # 1. Parse the prompt with Gemini
                    parsed_data = parse_prompt_with_gemini(prompt)

                    if parsed_data:
                        # Check for 'company' key first, then fall back to 'company_name'
                        company = (parsed_data.get("company", "") or parsed_data.get("company_name", "")).strip()
                        action = parsed_data.get("action", "").upper()

                        if not company:
                            notification_placeholder.markdown("<p class='notification-text' style='color: #9F6000;'>AI could not identify a company name. Please be more specific.</p>", unsafe_allow_html=True)
                            return

                        # 2. Perform the action (CREATE or UPDATE)
                        try:
                            # Find the row for the company (case-insensitive search)
                            cell_list = worksheet.findall(company, in_column=1, case_sensitive=False)
                            
                            if action == "CREATE" and not cell_list:
                                notification_placeholder.markdown(f"<p class='notification-text'>Adding new entry for **{company}**...</p>", unsafe_allow_html=True)
                                now = datetime.now().strftime("%Y-m-%d %H:%M:%S")
                                new_row = [
                                    company,
                                    parsed_data.get("job_title", ""),
                                    parsed_data.get("contact", ""),
                                    now.split(" ")[0], # Date Applied
                                    parsed_data.get("status", "Applied"),
                                    parsed_data.get("notes", ""),
                                    parsed_data.get("link", ""),
                                    parsed_data.get("salary", ""),
                                    parsed_data.get("location", ""),
                                    parsed_data.get("next_step_date", ""),
                                    parsed_data.get("recruiter_contact", ""),
                                    now # Last Updated
                                ]
                                worksheet.append_row(new_row)
                                notification_placeholder.markdown(f"<p class='notification-text' style='color: #4F8A10;'>Successfully added **{company}** to your sheet!</p>", unsafe_allow_html=True)

                            elif action == "UPDATE" or cell_list:
                                if not cell_list:
                                    notification_placeholder.markdown(f"<p class='notification-text' style='color: #9F6000;'>Could not find **{company}** to update. Try adding it first.</p>", unsafe_allow_html=True)
                                    return
                                    
                                notification_placeholder.markdown(f"<p class='notification-text'>Updating entry for **{company}**...</p>", unsafe_allow_html=True)
                                target_row = cell_list[0].row
                                
                                # Prepare updates, only changing what's new
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                updates = {
                                    'B': parsed_data.get("job_title"),
                                    'C': parsed_data.get("contact"),
                                    'E': parsed_data.get("status"),
                                    'F': parsed_data.get("notes"),
                                    'G': parsed_data.get("link"),
                                    'H': parsed_data.get("salary"),
                                    'I': parsed_data.get("location"),
                                    'J': parsed_data.get("next_step_date"),
                                    'K': parsed_data.get("recruiter_contact"),
                                    'L': now # Last Updated
                                }
                                
                                for col_letter, value in updates.items():
                                    if value: # Only update if the AI provided a value
                                        worksheet.update(f"{col_letter}{target_row}", value)

                                notification_placeholder.markdown(f"<p class='notification-text' style='color: #4F8A10;'>Successfully updated **{company}** in your sheet!</p>", unsafe_allow_html=True)
                            
                            else:
                                notification_placeholder.markdown(f"<p class='notification-text' style='color: #D8000C;'>Could not determine whether to create or update for {company}.</p>", unsafe_allow_html=True)


                        except Exception as e:
                            notification_placeholder.markdown(f"<p class='notification-text' style='color: #D8000C;'>An error occurred while updating the sheet: {e}</p>", unsafe_allow_html=True)

            else:
                notification_placeholder.markdown("<p class='notification-text' style='color: #9F6000;'>Please enter an update.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        # --- Display Sheet Data ---
        st.subheader("Dashboard")
        try:
            with st.spinner("Fetching latest data from Google Sheets..."):
                data = worksheet.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.markdown("<p class='empty-sheet-message'>Your sheet is currently empty. Add your first application!</p>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Could not fetch data from the sheet. {e}")


if __name__ == "__main__":
    main()
