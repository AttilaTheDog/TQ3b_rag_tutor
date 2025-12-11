"""
RAG-Tutor Frontend - Streamlit App
Progressive Hint System für IT-Admin/Cybersecurity Training
"""

import os
import streamlit as st
import requests

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="RAG-Tutor",
    page_icon="🎓",
    layout="wide"
)

# Session state initialization
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "hint_level" not in st.session_state:
    st.session_state.hint_level = 1


def login(username: str, password: str) -> bool:
    """Authenticate user and get token"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/token",
            data={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            
            # Get user info
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            user_response = requests.get(f"{BACKEND_URL}/me", headers=headers, timeout=10)
            if user_response.status_code == 200:
                st.session_state.user = user_response.json()
            return True
        return False
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
        return False


def logout():
    """Clear session"""
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.hint_level = 1


def get_hint(question: str, lab_context: str, hint_level: int) -> dict:
    """Get hint from backend"""
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        response = requests.post(
            f"{BACKEND_URL}/hint",
            headers=headers,
            json={
                "question": question,
                "lab_context": lab_context,
                "hint_level": hint_level
            },
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            logout()
            st.error("Sitzung abgelaufen. Bitte neu anmelden.")
            return None
        else:
            st.error(f"Fehler: {response.text}")
            return None
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
        return None


def upload_document(file) -> dict:
    """Upload PDF document (trainer only)"""
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
        response = requests.post(
            f"{BACKEND_URL}/upload",
            headers=headers,
            files=files,
            timeout=120
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Upload-Fehler: {response.text}")
            return None
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
        return None


def get_stats() -> dict:
    """Get system stats (trainer only)"""
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        response = requests.get(f"{BACKEND_URL}/stats", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


# ============================================================
# Main App
# ============================================================

st.title("🎓 RAG-Tutor")
st.caption("KI-gestützter Tutor für IT-Administration & Cybersecurity")

# Login Screen
if not st.session_state.token:
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 Anmeldung")
        
        with st.form("login_form"):
            username = st.text_input("Benutzername")
            password = st.text_input("Passwort", type="password")
            submit = st.form_submit_button("Anmelden", use_container_width=True)
            
            if submit:
                if login(username, password):
                    st.success("Erfolgreich angemeldet!")
                    st.rerun()
                else:
                    st.error("Falscher Benutzername oder Passwort")

# Main App (logged in)
else:
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['username']}")
        st.caption(f"Rolle: {st.session_state.user['role'].capitalize()}")
        
        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()
        
        st.markdown("---")
        
        # Trainer: Stats & Upload
        if st.session_state.user["role"] == "trainer":
            st.subheader("📊 System-Status")
            stats = get_stats()
            if stats:
                st.metric("Dokumente", stats.get("documents_count", "N/A"))
                st.caption(f"Qdrant: {'✅' if stats.get('qdrant_connected') else '❌'}")
                st.caption(f"LLM: {'✅' if stats.get('llm_connected') else '❌'}")
            
            st.markdown("---")
            
            st.subheader("📤 Dokumente hochladen")
            uploaded_files = st.file_uploader(
                "Dateien wählen",
                type=["pdf", "sql", "md", "txt"],
                accept_multiple_files=True,
                help="Laden Sie Schulungsmaterial als PDF, SQL, Markdwon oder Text-Dateien hoch (mehrere möglich)"
            )
            
            if uploaded_files:
                st.caption(f"{len(uploaded_files)} Datei(en) ausgewählt")
                if st.button("📥 Alle hochladen", use_container_width=True):
                    progress_bar = st.progress(0)
                    for i, uploaded_file in enumerate(uploaded_files):
                        with st.spinner(f"Verarbeite {uploaded_file.name}..."):
                            result = upload_document(uploaded_file)
                            if result:
                                st.success(f"✅ {result['filename']} ({result['chunks_created']} Chunks)")
                            progress_bar.progress((i + 1) / len(uploaded_files))
                    st.balloons()
    
    # Main Content Area
    st.markdown("---")
    
    # Hint Level Selection
    st.subheader("📚 Hinweis-Level")
    
    hint_levels = {
        1: ("🧠 Konzept", "Allgemeines Konzept und Theorie"),
        2: ("🔧 Tool/Bereich", "Welches Tool oder welcher Bereich"),
        3: ("📝 Syntax/Weg", "Konkreter Befehl oder Weg"),
        4: ("✅ Lösung", "Vollständige Lösung")
    }
    
    cols = st.columns(4)
    for i, (level, (name, desc)) in enumerate(hint_levels.items()):
        with cols[i]:
            if st.button(
                name,
                key=f"level_{level}",
                use_container_width=True,
                type="primary" if st.session_state.hint_level == level else "secondary"
            ):
                st.session_state.hint_level = level
                st.rerun()
    
    st.caption(f"Aktuell: **Level {st.session_state.hint_level}** - {hint_levels[st.session_state.hint_level][1]}")
    
    st.markdown("---")
    
    # Question Input
    st.subheader("❓ Deine Frage")
    
    question = st.text_area(
        "Was möchtest du wissen?",
        placeholder="z.B. Wie erstelle ich eine Firewall-Regel in Windows?",
        height=100,
        label_visibility="collapsed"
    )
    
    lab_context = st.text_input(
        "Lab-Kontext (optional)",
        placeholder="z.B. Windows Server 2022, Active Directory Umgebung",
        help="Zusätzlicher Kontext zur aktuellen Lab-Übung"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🎯 Hinweis erhalten", use_container_width=True, type="primary"):
            if question.strip():
                with st.spinner(f"Generiere Level-{st.session_state.hint_level} Hinweis..."):
                    result = get_hint(question, lab_context, st.session_state.hint_level)
                    
                    if result:
                        st.markdown("---")
                        st.subheader(f"💡 Hinweis ({result['hint_level_name']})")
                        st.markdown(result["hint"])
                        
                        if result["remaining_levels"] > 0:
                            st.info(f"📈 Noch {result['remaining_levels']} detailliertere Level verfügbar")
                        else:
                            st.success("✅ Maximales Detail-Level erreicht")
            else:
                st.warning("Bitte gib eine Frage ein")
    
    with col2:
        if st.session_state.hint_level < 4:
            if st.button("⬆️ Mehr Details", use_container_width=True):
                st.session_state.hint_level += 1
                st.rerun()

# Footer
st.markdown("---")
st.caption("RAG-Tutor v1.0 | Powered by LangChain & OpenAI")
