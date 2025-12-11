# RAG-Tutor 🎓

KI-gestützter Tutor für IT-Administration & Cybersecurity Training mit progressivem Hint-System.

**Stand: 11. Dezember 2025** - Alle Versionen aktuell!

## Versionen

| Komponente | Version | Release |
|------------|---------|---------|
| FastAPI | 0.124.2 | 10. Dez 2025 |
| uvicorn | 0.38.0 | Okt 2025 |
| LangChain | 1.x | Okt 2025 |
| langchain-qdrant | 0.2.x | 2025 |
| qdrant-client | 1.16.1 | Nov 2025 |
| Qdrant (Docker) | 1.16.2 | Dez 2025 |
| Streamlit | 1.52.1 | 5. Dez 2025 |
| pypdf | 6.4.1 | 2025 |
| Python | 3.11 | - |

## Quick Start

### 1. Repository auf Server kopieren

```bash
# Auf deinem lokalen Rechner
scp -r -i ~/.ssh/dein-key rag-tutor-fix root@DEIN-VPS-IP:/root/rag-tutor
```

### 2. Auf Server einloggen

```bash
ssh -i ~/.ssh/dein-key root@DEIN-VPS-IP
cd /root/rag-tutor
```

### 3. Environment einrichten

```bash
cp .env.example .env
nano .env  # Passe die Werte an!
```

### 4. Starten

```bash
docker compose up -d --build
```

### 5. Testen

- Frontend: http://DEIN-VPS-IP:8501
- Backend API: http://DEIN-VPS-IP:8000/docs
- Qdrant Dashboard: http://DEIN-VPS-IP:6333/dashboard

## Architektur

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│    Backend      │────▶│     Qdrant      │
│   (Streamlit)   │     │   (FastAPI)     │     │  (VectorDB)     │
│   Port: 8501    │     │   Port: 8000    │     │  Port: 6333     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │     OpenAI      │
                        │   (gpt-4o-mini) │
                        └─────────────────┘
```

## Progressive Hint-Levels

| Level | Name | Beschreibung |
|-------|------|--------------|
| 1 | Konzept | Allgemeines Konzept und Theorie |
| 2 | Tool/Bereich | Welches Tool oder welcher Bereich |
| 3 | Syntax/Weg | Konkreter Befehl oder Weg |
| 4 | Lösung | Vollständige Lösung |

## Benutzer

- **trainer** - Kann Dokumente hochladen und Statistiken sehen
- **student1-5** - Können Fragen stellen und Hints erhalten

## Befehle

```bash
# Status prüfen
docker compose ps

# Logs anzeigen
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f qdrant

# Neu starten
docker compose restart

# Komplett neu bauen
docker compose down
docker compose build --no-cache
docker compose up -d

# Qdrant Daten löschen (Vorsicht!)
docker compose down -v
```

## Dateistruktur

```
rag-tutor/
├── docker-compose.yaml
├── .env.example
├── .env                 # Manuell erstellen!
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
└── frontend/
    ├── Dockerfile
    ├── requirements.txt
    └── app.py
```


## Sicherheit

Für Produktionsumgebung:
1. Ändere alle Passwörter in `.env`
2. Nutze HTTPS (z.B. mit Caddy oder nginx)
3. Beschränke Firewall auf nötige Ports
4. Backup der Qdrant-Daten einrichten

## Lizenz

MIT License
