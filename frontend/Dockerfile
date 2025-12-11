FROM python:3.11-slim

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY app.py .

# Streamlit config
RUN mkdir -p ~/.streamlit
RUN echo '[server]\nheadless = true\nport = 8501\nenableCORS = false\n' > ~/.streamlit/config.toml

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
