"""
RAG-Tutor Backend - Cybersecurity/IT-Admin Training Assistant
Progressive Hint System für TalentLMS Integration
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager

# FastAPI
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Auth
from jose import JWTError, jwt
from passlib.context import CryptContext

# LangChain Core (1.x - Dezember 2025)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

# LangChain Text Splitters
from langchain_text_splitters import RecursiveCharacterTextSplitter

# LangChain OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# LangChain Qdrant (QdrantVectorStore statt deprecated Qdrant)
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# PDF Processing
from pypdf import PdfReader

# ============================================================
# Configuration
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "trainer2024")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "rag_tutor_docs"

# JWT Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 Stunden

# ============================================================
# Auth Setup
# ============================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_users():
    """User-Datenbank mit konfigurierbaren Passwörtern"""
    return {
        "trainer": {
            "password_hash": pwd_context.hash(ADMIN_PASSWORD),
            "role": "trainer"
        },
        "student01": {
            "password_hash": pwd_context.hash(os.getenv("STUDENT1_PW", "student01")),
            "role": "schueler"
        },
        "student02": {
            "password_hash": pwd_context.hash(os.getenv("STUDENT2_PW", "student02")),
            "role": "schueler"
        },
        "student03": {
            "password_hash": pwd_context.hash(os.getenv("STUDENT3_PW", "student03")),
            "role": "schueler"
        },
        "student04": {
            "password_hash": pwd_context.hash(os.getenv("STUDENT4_PW", "student04")),
            "role": "schueler"
        },
        "student05": {
            "password_hash": pwd_context.hash(os.getenv("STUDENT5_PW", "student05")),
            "role": "schueler"
        },
        "student06": {
            "password_hash": pwd_context.hash(os.getenv("STUDENT6_PW", "student06")),
            "role": "schueler"
        },
        "student07": {
            "password_hash": pwd_context.hash(os.getenv("STUDENT7_PW", "student07")),
            "role": "schueler"
        },
    }


# ============================================================
# Pydantic Models
# ============================================================

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class User(BaseModel):
    username: str
    role: str


class HintRequest(BaseModel):
    question: str
    lab_context: Optional[str] = ""
    hint_level: int = 1  # 1-4: Konzept → Tool → Syntax → Lösung


class HintResponse(BaseModel):
    hint: str
    hint_level: int
    hint_level_name: str
    remaining_levels: int


class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_created: int


# ============================================================
# Global Variables
# ============================================================

vectorstore: Optional[QdrantVectorStore] = None
llm: Optional[ChatOpenAI] = None
embeddings: Optional[OpenAIEmbeddings] = None


# ============================================================
# Lifespan & App Setup
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    global vectorstore, llm, embeddings
    
    print("🚀 Starting RAG-Tutor Backend...")
    
    # Initialize OpenAI
    if OPENAI_API_KEY:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=OPENAI_API_KEY
        )
        embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        print("✅ OpenAI initialized")
    else:
        print("⚠️ OPENAI_API_KEY not set!")
    
    # Initialize Qdrant
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if COLLECTION_NAME not in collection_names:
            # Create collection with OpenAI embedding dimensions (1536)
            from qdrant_client.http.models import Distance, VectorParams
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
            print(f"✅ Created Qdrant collection: {COLLECTION_NAME}")
        
        # Initialize QdrantVectorStore
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings
        )
        print("✅ Qdrant connected")
        
    except Exception as e:
        print(f"⚠️ Qdrant connection error: {e}")
    
    yield
    
    print("👋 Shutting down RAG-Tutor Backend...")


app = FastAPI(
    title="RAG-Tutor API",
    description="AI-gestützter Tutor für IT-Admin/Cybersecurity Training",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Auth Functions
# ============================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str):
    users = get_users()
    if username not in users:
        return None
    user = users[username]
    if not verify_password(password, user["password_hash"]):
        return None
    return {"username": username, "role": user["role"]}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültige Anmeldedaten",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        return User(username=username, role=role)
    except JWTError:
        raise credentials_exception


async def require_trainer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "trainer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Trainer haben Zugriff auf diese Funktion"
        )
    return current_user


# ============================================================
# Progressive Hint System
# ============================================================

HINT_LEVELS = {
    1: {
        "name": "Konzept",
        "description": "Allgemeines Konzept und Theorie",
        "prompt_instruction": "Erkläre nur das grundlegende Konzept oder die Theorie hinter der Frage. Gib KEINE konkreten Befehle oder Tools an. Halte die Antwort kurz (2-3 Sätze)."
    },
    2: {
        "name": "Tool/Bereich",
        "description": "Welches Tool oder welcher Bereich",
        "prompt_instruction": "Nenne das relevante Tool, Programm oder den Konfigurationsbereich. Gib noch KEINE konkreten Befehle oder Syntax. Beispiel: 'Du brauchst den Dienste-Manager' oder 'Schau in die Firewall-Einstellungen'."
    },
    3: {
        "name": "Syntax/Weg",
        "description": "Konkreter Befehl oder Weg",
        "prompt_instruction": "Gib den konkreten Befehl, Menüpfad oder die Syntax an. Der Schüler soll es selbst ausführen können. Erkläre kurz die Parameter."
    },
    4: {
        "name": "Lösung",
        "description": "Vollständige Lösung",
        "prompt_instruction": """Gib die vollständige Lösung mit allen Schritten. Erkläre was jeder Schritt bewirkt.
- Gehe JEDEN einzelnen Schritt durch, der im Kontext steht
- Verwende EXAKT die IPs, Gateways und Werte aus dem Kontext
- ERFINDE KEINE Details die nicht im Kontext stehen
- Wenn etwas unklar ist, sage es
- Formatiere übersichtlich mit nummerierten Schritten"""
    }
}


def build_hint_prompt(question: str, context: str, lab_context: str, hint_level: int) -> str:
    """Erstellt den Prompt basierend auf Hint-Level"""
    
    level_info = HINT_LEVELS.get(hint_level, HINT_LEVELS[1])
    
    system_prompt = f"""Du bist ein Tutor für IT-Administration und Cybersecurity.
Du hilfst Schülern bei Lab-Übungen, indem du progressive Hinweise gibst.

AKTUELLER HINT-LEVEL: {hint_level} ({level_info['name']})
ANWEISUNG: {level_info['prompt_instruction']}

WICHTIG:
- Antworte auf Deutsch
- Sei präzise und klar
- Gib NUR Informationen passend zum aktuellen Level
- Wenn der Kontext nicht ausreicht, sage das ehrlich
- Verwende EXAKT die IPs, Subnetze, Gateways aus dem Kontext
- ERFINDE KEINE Werte die nicht im Kontext oder den Unterlagen stehen
- Wenn Information fehlt, sage: "Diese Information steht nicht in den Unterlagen"
- Antworte auf Deutsch
- Sei präzise und vollständig
- Gehe JEDEN einzelnen Schritt durch, der im Kontext steht
- BEHALTE Variablen-Notation bei: 192.168.x.0 statt konkreter IPs
- Erkläre dass x = Labor-ID des Students (student03 → x=3)
- ERFINDE KEINE konkreten IP-Adressen
- Wenn der User seinen Lab-Kontext angibt, ersetze x durch seine Nummer"""

    user_prompt = f"""FRAGE DES SCHÜLERS:
{question}

KONTEXT AUS DER WISSENSBASIS (wenn du andere Infos verwendest, markiere diese eindeutig als -nicht aus Wisensbasis-):
{context}

LAB-KONTEXT:
{lab_context if lab_context else 'Kein spezifischer Lab-Kontext angegeben'}

Gib einen Hinweis auf Level {hint_level} ({level_info['name']})."""

    return system_prompt, user_prompt


# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    return {
        "message": "RAG-Tutor API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "qdrant": vectorstore is not None,
        "llm": llm is not None
    }


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login und JWT Token erhalten"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falscher Benutzername oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Aktuellen Benutzer abrufen"""
    return current_user


@app.post("/hint", response_model=HintResponse)
async def get_hint(
    request: HintRequest,
    current_user: User = Depends(get_current_user)
):
    """Progressive Hinweise für Lab-Fragen"""
    
    if not llm or not vectorstore:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend-Services nicht verfügbar"
        )
    
    # Validate hint level
    hint_level = max(1, min(4, request.hint_level))
    
    # RAG: Relevante Dokumente suchen
    try:
        docs = vectorstore.similarity_search(request.question, k=8)
        context = "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        print(f"Qdrant search error: {e}")
        context = "Keine relevanten Dokumente gefunden."
    
    # Prompt bauen
    system_prompt, user_prompt = build_hint_prompt(
        request.question,
        context,
        request.lab_context,
        hint_level
    )
    
    # LLM aufrufen
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        
        chain = prompt | llm | StrOutputParser()
        hint = chain.invoke({})
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei der Hint-Generierung: {str(e)}"
        )
    
    level_info = HINT_LEVELS[hint_level]
    
    return HintResponse(
        hint=hint,
        hint_level=hint_level,
        hint_level_name=level_info["name"],
        remaining_levels=4 - hint_level
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_trainer)
):
    """Dokument hochladen (nur Trainer) - PDF, SQL, MD, TXT"""
    
    if not vectorstore or not embeddings:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend-Services nicht verfügbar"
        )
    
    # Erlaubte Dateitypen
    allowed_extensions = ['.pdf', '.sql', '.md', '.txt']
    file_ext = os.path.splitext(file.filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nur {', '.join(allowed_extensions)} Dateien werden unterstützt"
        )
    
    try:
        content = await file.read()
        
        # Text extrahieren basierend auf Dateityp
        if file_ext == '.pdf':
            # PDF parsen
            temp_path = f"/tmp/{file.filename}"
            with open(temp_path, "wb") as f:
                f.write(content)
            
            reader = PdfReader(temp_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            os.remove(temp_path)
        else:
            # Text-Dateien direkt lesen (.sql, .md, .txt)
            text = content.decode('utf-8')
        
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Datei enthält keinen extrahierbaren Text"
            )
        
        # Text in Chunks aufteilen
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        
        # Dokumente erstellen
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "source": file.filename,
                    "file_type": file_ext,
                    "uploaded_by": current_user.username,
                    "uploaded_at": datetime.utcnow().isoformat()
                }
            )
            for chunk in chunks
        ]
        
        # Zu Qdrant hinzufügen
        vectorstore.add_documents(documents)
        
        return UploadResponse(
            message="Dokument erfolgreich hochgeladen",
            filename=file.filename,
            chunks_created=len(chunks)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Verarbeiten: {str(e)}"
        )


@app.get("/stats")
async def get_stats(current_user: User = Depends(require_trainer)):
    """Statistiken abrufen (nur Trainer)"""
    
    stats = {
        "users": list(get_users().keys()),
        "qdrant_connected": vectorstore is not None,
        "llm_connected": llm is not None
    }
    
    if vectorstore:
        try:
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            collection_info = client.get_collection(COLLECTION_NAME)
            stats["documents_count"] = collection_info.points_count
        except Exception as e:
            stats["documents_count"] = f"Error: {e}"
    
    return stats
