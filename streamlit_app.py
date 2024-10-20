import streamlit as st
import requests
from datetime import datetime
import uuid
import json
import calendar
import re
import os
from dotenv import load_dotenv
from streamlit_feedback import streamlit_feedback
import time

load_dotenv()

# FastAPI backend URL
API_URL = "https://civic-marlena-finpro-be745773.koyeb.app/"  # Keep your original API URL

def send_message(username, message, session_id, paths):
    response = requests.post(
        f"{API_URL}/chat/",
        json={"input": message, "username": username, "session_id": session_id, "paths": paths}
    )
    return response.json() if response.status_code == 200 else None

def clear_message_history(username, session_id):
    response = requests.post(
        f"{API_URL}/clear_history/",
        json={"username": username, "session_id": session_id}
    )
    return response.status_code == 200

def register_user(username, name, email, password):
    response = requests.post(
        f"{API_URL}/register",
        json={"username": username, "name": name, "email": email, "password": password}
    )
    return response.json() if response.status_code == 200 else None

def login_user(username, password):
    response = requests.post(
        f"{API_URL}/login",
        json={"username": username, "password": password}
    )
    return response.json() if response.status_code == 200 else None

def send_feedback(username, message_id, feedback_type, score, comment):
    response = requests.post(
        f"{API_URL}/feedback/",
        json={
            "message_id": message_id,
            "feedback_type": feedback_type,
            "score": score,
            "comment": comment
        },
        params={"username": username}
    )
    return response.json() if response.status_code == 200 else None


def folder_selector():
    st.title("Select the Company and the earning calls")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        metadata_path = os.path.join(current_dir, "metadata.json")
        #st.write(f"Attempting to load metadata from: {metadata_path}")
        
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as file:
                metadata = json.load(file)
            st.success("Companies loaded successfully")
            #st.write(f"Number of entries in metadata: {len(metadata)}")
        else:
            st.error(f"metadata.json not found at {metadata_path}")
            return []
    except Exception as e:
        st.error(f"Error loading metadata: {str(e)}")
        return []

    # # Investigate source paths
    # st.write("Sample source paths:")
    # for i, entry in enumerate(metadata[:5]):  # Show first 5 entries
    #     st.write(f"Entry {i + 1}: {entry['source']}")

    # Extract company names more robustly
    def extract_company(source):
        # Replace backslashes with forward slashes to handle Windows paths
        source = source.replace("\\", "/")
        parts = source.split("/")
        if "Concalls" in parts:
            idx = parts.index("Concalls")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return None

    unique_companies = list(set(filter(None, [extract_company(entry["source"]) for entry in metadata])))
    unique_companies.sort()
    # st.write(f"Number of unique companies: {len(unique_companies)}")
    # st.write(f"Unique companies: {unique_companies}")

    # Create a dropdown for selecting the company
    if unique_companies:
        selected_company = st.selectbox("Select a Company:", unique_companies, key="company_selector")
    else:
        st.error("No companies found in the metadata.")
        return []

    # Filter metadata based on the selected company
    company_metadata = [entry for entry in metadata if extract_company(entry["source"]) == selected_company]

    years_months = extract_year_month_from_metadata(company_metadata)
    if years_months:
        # Get unique years
        unique_years = list(set([year for year, _ in years_months]))
        unique_years.sort(reverse=True)

        # Create a dropdown for selecting the year
        selected_year = st.selectbox("Select a Year:", unique_years, key="year_selector")

        # Filter years_months based on the selected year
        selected_years_months = [(year, month) for year, month in years_months if year == selected_year]

        if selected_years_months:
            # Get unique months for the selected year
            unique_months = list(set([calendar.month_name[int(month)] for _, month in selected_years_months]))
            unique_months.sort(key=lambda m: list(calendar.month_name).index(m))

            selected_month = st.selectbox("Select Month:", unique_months, key="month_selector")
            selected_paths = []
            for entry in company_metadata:
                if (
                    (selected_month[:3].lower() in entry["source"].lower() or selected_month[:3].upper() in entry["source"].lower()) and
                    (entry["source"].endswith(".pdf") or entry["source"].endswith(".PDF"))
                ):
                    filename_without_date = re.findall(r".*_([^\.]+)\.", entry["source"])[0]
                    path_year = extract_year_from_path(entry["source"])
                    
                    if (
                        filename_without_date in entry["source"].split("/")[-1] and
                        path_year == selected_year[2:]
                    ):  
                        selected_paths.append(entry["source"])

            return selected_paths

    return []

def extract_year_month_from_metadata(metadata):
    years_months = []
    for entry in metadata:
        match = re.search(r'(\w{3})(\d{2})', entry["source"])
        if match:
            month_abbreviation = match.group(1)
            year_short = match.group(2)

            month_mapping = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }

            month_numeric = month_mapping.get(month_abbreviation.lower())

            if month_numeric:
                year = '20' + year_short
                years_months.append((year, month_numeric))

    return years_months

def extract_year_from_path(path):
    match = re.search(r'(\d{2,4})', path)
    if match:
        return match.group(1)
    else:
        print(f"No year found in path: {path}")
        return None


def main():
    st.set_page_config(page_title="Finpro - EarningsWhisperer", page_icon="💹", layout="wide")
    st.title("Finpro - EarningsWhisperer 💹")

    if 'user' not in st.session_state:
        st.session_state.user = {'username': '', 'session_id': ''}

    if not st.session_state.user['username']:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                user = login_user(username, password)
                if user:
                    st.session_state.user['username'] = user['username']
                    st.session_state.user['session_id'] = user['session_id']
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        with tab2:
            st.subheader("Register")
            new_username = st.text_input("Username", key="register_username")
            new_full_name = st.text_input("Full Name", key="register_full_name")
            new_email = st.text_input("Email", key="register_email")
            new_password = st.text_input("Password", type="password", key="register_password")
            if st.button("Register"):
                user = register_user(new_username, new_full_name, new_email, new_password)
                if user:
                    st.session_state.user['username'] = user['username']
                    st.session_state.user['session_id'] = user['session_id']
                    st.success("Registered successfully! You can now log in.")
                    st.rerun()
                else:
                    st.error("Registration failed. Username or email might already exist.")

    else:
        with st.sidebar:
            st.subheader(f"Welcome, {st.session_state.user['username']}!")
            st.session_state.path = folder_selector()

            if st.button("Clear Message History"):
                if clear_message_history(st.session_state.user['username'], st.session_state.user['session_id']):
                    st.session_state.messages = []
                    st.success("Message history cleared successfully.")
                else:
                    st.error("Failed to clear message history.")

            if st.button("Logout"):
                st.session_state.user = {'username': '', 'session_id': ''}
                st.session_state.messages = []
                st.rerun()

        if 'messages' not in st.session_state:
            st.session_state.messages = []

        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
            
            if message["role"] == "assistant":
                if "sources" in message:
                    with st.expander("View Sources"):
                        if message["sources"]:
                            for idx, source in enumerate(message["sources"]):
                                st.markdown(f"**Source {idx + 1}:**")
                                st.markdown(f"**File:** {source['metadata'].get('source', 'N/A')}")
                                st.markdown(f"**Page:** {source['metadata'].get('page', 'N/A')}")
                                with st.container():
                                    st.markdown('<div class="scrollable-container">', unsafe_allow_html=True)
                                    st.markdown(f"**Content:**\n\n{source['page_content']}")
                                    st.markdown('</div>', unsafe_allow_html=True)
                                st.markdown("---")
                        else:
                            st.write("No sources available for this response.")

                feedback = streamlit_feedback(
                    feedback_type="faces",
                    optional_text_label="[Optional] Please provide an explanation",
                    key=f"feedback_{message.get('id', '')}_{i}",
                )
                if feedback:
                    scores = {"😀": 1, "🙂": 0.75, "😐": 0.5, "🙁": 0.25, "😞": 0}
                    success = send_feedback(
                        st.session_state.user['username'],
                        message.get('id', ''),
                        feedback["type"],
                        scores[feedback["score"]],
                        feedback.get("text", "")
                    )
                    if success:
                        st.success("Feedback submitted successfully!")
                    else:
                        st.error("Failed to submit feedback. Please try again.")

        if prompt := st.chat_input("What is your question?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                with st.spinner("Processing..."):
                    response = send_message(
                        st.session_state.user['username'],
                        prompt,
                        st.session_state.user['session_id'],
                        st.session_state.path
                    )
                    print(response)
                
                if response:
                    message_placeholder.markdown(response["response"])
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response["response"], 
                        "id": response["message_id"],
                        "sources": response.get("sources", [])
                    })
                    
                    with st.expander("View Sources"):
                        if response.get("sources"):
                            for idx, source in enumerate(response["sources"]):
                                st.markdown(f"**Source {idx + 1}:**")
                                st.markdown(f"**File:** {source['metadata'].get('source', 'N/A')}")
                                st.markdown(f"**Page:** {source['metadata'].get('page', 'N/A')}")
                                with st.container():
                                    st.markdown('<div class="scrollable-container">', unsafe_allow_html=True)
                                    st.markdown(f"**Content:**\n\n{source['page_content']}")
                                    st.markdown('</div>', unsafe_allow_html=True)
                                st.markdown("---")
                        else:
                            st.write("No sources available for this response.")
                else:
                    message_placeholder.error("Failed to get a response from the AI. Please try again.")

                st.rerun()

if __name__ == "__main__":
    main()
