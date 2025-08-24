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
    page_title="AI Job Application Tracker",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
        # Load credentials from Streamlit secrets
        # IMPORTANT: Your secrets.toml file should look like this:
        # [gcp_service_account]
        # type = "service_account"
        # project_id = "your-project-id"
        # ... (all the other keys from your JSON file) ...
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
    # IMPORTANT: You don't need to provide an API key if using a supported model.
    # The environment will handle authentication automatically.
    api_key = "" 
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

    # The detailed instruction for the model
    system_prompt = """
    You are an intelligent assistant for a job application tracker. 
    Your task is to extract structured information from the user's text.
    Analyze the text to determine if it's a new application ('CREATE') or an update to an existing one ('UPDATE').
    Extract the company name, contact (email or platform like LinkedIn), the application status, and any relevant notes.

    - For 'status', use one of these predefined categories: 'Applied', 'Assessment', 'Interview Scheduled', 'Offer Received', 'Rejected', 'Followed Up', 'Withdrew'.
    - If the user mentions sending an application, the status is 'Applied'.
    - If the user mentions a response, interview, or next steps, the action is 'UPDATE'.
    - If a field isn't mentioned, set its value to an empty string "".

    Respond ONLY with a JSON object.
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
    st.title("📝 AI-Powered Job Application Tracker")
    st.markdown("Simply type what you did, and the AI will update your Google Sheet. Try things like: *'Sent my application to Stripe via their website'* or *'Heard back from Google, phone screen next Tuesday at 2pm'*.")
    st.markdown("---")

    # --- Setup Instructions Expander ---
    with st.expander("🔑 First-Time Setup Instructions (Click to Expand)"):
        st.markdown("""
        To use this app, you need to connect it to your Google Sheet. This requires a one-time setup:

        **1. Create a Google Sheet:**
           - Make a new Google Sheet.
           - Name the first sheet (tab) `Applications`.
           - Create the following headers in the first row: `Company`, `Contact`, `Date Applied`, `Status`, `Notes`, `Last Updated`.

        **2. Set up Google Cloud Service Account:**
           - Go to the [Google Cloud Console](https://console.cloud.google.com/).
           - Create a new project.
           - Enable the **Google Sheets API** and **Google Drive API** for your project.
           - Create a **Service Account**. Go to `IAM & Admin` > `Service Accounts`.
           - Create a key for the service account (choose JSON format). A JSON file will be downloaded. This contains your credentials.

        **3. Share Your Google Sheet:**
           - Open the JSON file you downloaded. Find the `client_email` address.
           - In your Google Sheet, click the "Share" button.
           - Paste the `client_email` and give it "Editor" permissions.

        **4. Add Credentials to Streamlit Secrets:**
           - In your Streamlit project folder, create a new folder called `.streamlit`.
           - Inside `.streamlit`, create a file named `secrets.toml`.
           - Copy the contents of the downloaded JSON file and paste it into `secrets.toml` under the heading `[gcp_service_account]`.
           
           Your `secrets.toml` file should look like this:
           ```toml
           [gcp_service_account]
           type = "service_account"
           project_id = "your-gcp-project-id"
           private_key_id = "your-private-key-id"
           private_key = "-----BEGIN PRIVATE KEY-----\\n...your-private-key...\\n-----END PRIVATE KEY-----\\n"
           client_email = "your-service-account-email@your-project-id.iam.gserviceaccount.com"
           client_id = "your-client-id"
           # ... and so on for all keys in the JSON file.
           ```
        **5. Add Google Sheet Name to Secrets:**
            - Add the exact name of your Google Sheet file to your `secrets.toml`:
            ```toml
            GSHEET_NAME = "Your Google Sheet File Name"
            ```
        """)

    # --- Main Interface ---
    
    # Connect to Google Sheets
    client = connect_to_gsheet()

    if client:
        try:
            GSHEET_NAME = st.secrets["GSHEET_NAME"]
            spreadsheet = client.open(GSHEET_NAME)
            worksheet = spreadsheet.worksheet("Applications")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Spreadsheet named '{st.secrets.get('GSHEET_NAME', 'GSHEET_NAME_not_found')}' not found. Please check the Gsheet name in your secrets and ensure it's shared with the service account.")
            return
        except gspread.exceptions.WorksheetNotFound:
            st.error("Worksheet named 'Applications' not found. Please make sure the first tab in your sheet is named exactly that.")
            return
        except Exception as e:
            st.error(f"An error occurred while opening the sheet: {e}")
            return

        # --- User Input ---
        prompt = st.text_input("What's your update?", placeholder="e.g., Applied to Vercel for the frontend engineer role...")

        if st.button("Update Sheet", type="primary"):
            if prompt:
                with st.spinner("🤖 AI is processing your request..."):
                    # 1. Parse the prompt with Gemini
                    parsed_data = parse_prompt_with_gemini(prompt)

                    if parsed_data:
                        st.success("AI analysis complete!")
                        st.json(parsed_data) # Show the user what the AI understood

                        company = parsed_data.get("company_name", "").strip()
                        action = parsed_data.get("action", "").upper()

                        if not company:
                            st.warning("AI could not identify a company name. Please be more specific.")
                            return

                        # 2. Perform the action (CREATE or UPDATE)
                        try:
                            # Find the row for the company (case-insensitive search)
                            cell_list = worksheet.findall(company, in_column=1, case_sensitive=False)
                            
                            if action == "CREATE" and not cell_list:
                                st.info(f"Adding new entry for **{company}**...")
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                new_row = [
                                    company,
                                    parsed_data.get("contact", ""),
                                    now.split(" ")[0], # Date Applied
                                    parsed_data.get("status", "Applied"),
                                    parsed_data.get("notes", ""),
                                    now # Last Updated
                                ]
                                worksheet.append_row(new_row)
                                st.success(f"Successfully added **{company}** to your sheet!")

                            elif action == "UPDATE" or cell_list:
                                if not cell_list:
                                    st.warning(f"Could not find **{company}** to update. Try adding it first.")
                                    return
                                    
                                st.info(f"Updating entry for **{company}**...")
                                target_row = cell_list[0].row
                                
                                # Prepare updates, only changing what's new
                                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                updates = {
                                    'D': parsed_data.get("status"), # Column D for Status
                                    'E': parsed_data.get("notes"),   # Column E for Notes
                                    'F': now                         # Column F for Last Updated
                                }
                                
                                for col_letter, value in updates.items():
                                    if value: # Only update if the AI provided a value
                                        worksheet.update(f"{col_letter}{target_row}", value)

                                st.success(f"Successfully updated **{company}** in your sheet!")
                            
                            else:
                                st.error(f"Could not determine whether to create or update for {company}. The AI action was '{action}' and a sheet entry was {'found' if cell_list else 'not found'}.")


                        except Exception as e:
                            st.error(f"An error occurred while updating the sheet: {e}")

            else:
                st.warning("Please enter an update.")

        # --- Display Sheet Data ---
        st.markdown("---")
        st.subheader("📊 Your Application Dashboard")
        try:
            with st.spinner("Fetching latest data from Google Sheets..."):
                data = worksheet.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Your sheet is currently empty. Add your first application!")
        except Exception as e:
            st.error(f"Could not fetch data from the sheet. {e}")


if __name__ == "__main__":
    main()
