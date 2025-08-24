# Automated Application Tracker

<p align="center">
  <em>An intelligent job application tracker built with Streamlit and powered by the Gemini API. Update your job search progress in a Google Sheet using natural language.</em>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img alt="Google Cloud" src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white"/>
</p>

<br>

<p align="center">
  <img width="1833" height="784" alt="Main application interface" src="https://github.com/user-attachments/assets/fbebc0b2-6ce4-4c24-9b3c-c9b4c53db2f1">
</p>

---

## Features

<table>
  <tr>
    <td>
      <h3>Natural Language Input</h3>
      <p>Simply type updates in plain English. No more tedious manual data entry. The app understands your intent and context.</p>
    </td>
    <td align="center">
      <img width="1011" height="305" alt="Natural language input example" src="https://github.com/user-attachments/assets/aecec3f4-d07c-4b9e-a7ce-24078cf3d344">
    </td>
  </tr>
  <tr>
    <td>
      <h3>Google Sheets Integration</h3>
      <p>Automatically creates new rows for new applications and intelligently updates existing ones based on your prompts.</p>
    </td>
    <td align="center">
      <img width="1459" height="501" alt="Google Sheet being updated" src="https://github.com/user-attachments/assets/207e8947-6fb9-4165-88af-4dadf34d9caf">
    </td>
  </tr>
  <tr>
    <td>
      <h3>Clean Dashboard View</h3>
      <p>View your entire application history in a clean, scrollable table directly within the app, keeping you organized and focused.</p>
    </td>
    <td align="center">
      <img width="744" height="372" alt="Application dashboard view" src="https://github.com/user-attachments/assets/065e8e34-c3e8-4e28-857d-aedbe7708b38">
    </td>
  </tr>
</table>

---

## 🚀 Getting Started

Follow these steps to get your own instance of the Automated Application Tracker up and running.

<details>
<summary><strong>📝 Step 1: Prepare Your Google Sheet</strong></summary>
<br>
  
1.  Go to [sheets.google.com](https://sheets.google.com) and create a **new, blank spreadsheet**.
2.  Name the spreadsheet whatever you like (e.g., "My Job Applications").
3.  Rename the first tab at the bottom to **`Applications`**.
4.  In the first row, create the following headers exactly as written:
    -   `Company`
    -   `Job Title`
    -   `Contact`
    -   `Date Applied`
    -   `Status`
    -   `Notes`
    -   `Link to Application`
    -   `Salary`
    -   `Location`
    -   `Next Step Date`
    -   `Recruiter Contact`
    -   `Last Updated`
</details>

<details>
<summary><strong>☁️ Step 2: Configure Google Cloud & APIs</strong></summary>
<br>
  
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a **New Project**.
2.  **Enable Billing** for the project. You will not be charged for usage within the free tier.
3.  Enable the following three APIs for your project:
    -   **Google Sheets API**
    -   **Google Drive API**
    -   **Generative Language API**
4.  Create a **Service Account**:
    -   Navigate to `IAM & Admin` > `Service Accounts`.
    -   Click `+ CREATE SERVICE ACCOUNT`, give it a name, and assign it the **Editor** role.
    -   Create and download a **JSON key** for the service account.
5.  Create an **API Key**:
    -   Navigate to `APIs & Services` > `Credentials`.
    -   Click `+ CREATE CREDENTIALS` and select `API key`.
    -   Copy the key and restrict it to the **Generative Language API**.
</details>

<details>
<summary><strong>🔗 Step 3: Connect Your App to Google</strong></summary>
<br>
  
1.  **Share Your Google Sheet**:
    -   Open the downloaded JSON key file and copy the `client_email` address.
    -   In your Google Sheet, click the "Share" button and give **Editor** permissions to that `client_email`.
2.  **Create `secrets.toml`**:
    -   In your project folder, create a new folder named `.streamlit`.
    -   Inside it, create a file named `secrets.toml`.
    -   Populate it with your credentials as shown below. Remember to convert your service account JSON to TOML format (replace colons with equals signs, remove commas, etc.).

    ```toml
    # .streamlit/secrets.toml

    GSHEET_NAME = "Your Google Sheet File Name"
    GEMINI_API_KEY = "your_newly_created_api_key"

    [gcp_service_account]
    type = "service_account"
    project_id = "your-gcp-project-id"
    private_key_id = "your-private-key-id"
    private_key = "-----BEGIN PRIVATE KEY-----\\n...your-private-key...\\n-----END PRIVATE KEY-----\\n"
    client_email = "your-service-account-email@..."
    client_id = "your-client-id"
    auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
    token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
    auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
    client_x509_cert_url = "https://..."
    universe_domain = "googleapis.com"
    ```
</details>

<details>
<summary><strong>▶️ Step 4: Run the Application</strong></summary>
<br>
  
1.  **Install Dependencies**:
    -   Create a `requirements.txt` file with the following content:
    ```
    streamlit
    gspread
    pandas
    google-oauth2-service-account
    requests
    ```
    -   Install them using pip: `pip install -r requirements.txt`
2.  **Run the App**:
    -   Open your terminal, navigate to your project folder, and run:
    ```bash
    streamlit run app.py
    ```
</details>
