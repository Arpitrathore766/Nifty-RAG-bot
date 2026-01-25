import streamlit as st
import requests

# Page Config
st.set_page_config(page_title="Nifty 50 RAG Bot", page_icon="📈")
st.title("📈 Nifty 50 AI Analyst")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask about Nifty 50 stocks..."):
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Call Backend API
    with st.chat_message("assistant"):
        with st.spinner("Analyzing market data..."):
            try:
                response = requests.post(
                    "http://localhost:8000/chat", 
                    json={"query": prompt}
                )
                if response.status_code == 200:
                    answer = response.json().get("answer", "No answer received.")
                else:
                    answer = f"Error: {response.text}"
            except Exception as e:
                answer = f"Connection Error: {e}"
        
        st.markdown(answer)
    
    # 3. Add Assistant Message to History
    st.session_state.messages.append({"role": "assistant", "content": answer})