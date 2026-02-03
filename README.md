# Google Maps Sentiment Analysis API

Sistema avanzado de extracción y análisis de reseñas de Google Maps. Este proyecto combina **Web Scraping** (Playwright), **Procesamiento de Lenguaje Natural** (Transformers) y **APIs REST** (FastAPI) para generar insights automáticos sobre negocios.

## 🚀 Características Principales

*   **Scraping Indetectable**: Uso de Playwright con estrategias de evasión de bots y autenticación mediante Cookies.
*   **Análisis de Sentimientos (NLP)**: Integración de modelos Transformers (Robertuito/BETO) para clasificar reseñas en Español (Positivo, Negativo, Neutral) con score de confianza.
*   **API REST**: Endpoint rápido construído con FastAPI para integrar en otros sistemas.
*   **Cache Persistente**: Uso de **PostgreSQL** para almacenar resultados y evitar scraping redundante.
*   **Cloud Ready**: Configurado para despliegue en Render (Docker/Native).

---

## 🛠️ Instalación

1.  **Clonar el repositorio**:
    ```bash
    git clone <repo-url>
    cd modelScrap
    ```

2.  **Instalar dependencias**:
    Se recomienda usar un entorno virtual (`venv`).
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
    *Nota: Esto descargará librerías pesadas como PyTorch y Transformers.*

3.  **Configurar Variables de Entorno**:
    Crea un archivo `.env` o configura las variables en tu sistema:
    ```bash
    # URL de conexión a PostgreSQL (Opcional en local, obligatorio en Prod)
    DATABASE_URL=postgresql://user:password@host:port/dbname
    
    # Opcional: Saltar carga de modelos al inicio (para debug rápido)
    # SKIP_NLP_LOAD=true
    ```

---

## 🍪 Configuración de Autenticación (Google Login)

Google bloquea los logins automatizados en la nube. Para solucionarlo, usamos **Cookies de Sesión**.

1.  **Ejecutar el asistente de login local**:
    ```bash
    python scraper.py --setup-cookies
    ```
2.  Se abrirá un navegador Chrome.
3.  Inicia sesión manualmente en Google.
4.  Presiona `ENTER` en la terminal cuando hayas terminado.
5.  Se generará el archivo `cookies.json`.
6.  **Importante**: Si despliegas en Render, asegúrate de subir este archivo o gestionarlo como secret.

---

## 💻 Uso

### 1. Servidor API (Recomendado)

Levanta el servidor FastAPI. La primera vez descargará el modelo de IA (~500MB).

```bash
uvicorn api:app --reload
```

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Endpoint**: `POST /analyze`

#### Ejemplo de Petición
```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
     -H "Content-Type: application/json" \
     -d '{
           "maps_url": "https://maps.app.goo.gl/Ti7ixa3owkmGMdTo9",
           "limit": 20,
           "forceUpdate": false
         }'
```

#### Respuesta JSON
```json
{
  "business_name": "Nombre del Negocio",
  "total_reviews": 20,
  "average_rating": 4.5,
  "sentiment_summary": {
    "POS": 15,
    "NEG": 2,
    "NEU": 3
  },
  "reviews": [
    {
      "username": "Usuario 1",
      "rating": 5,
      "review_text": "Excelente servicio...",
      "sentiment": "POS",
      "confidence": 0.98
    }
  ],
  "cached": false
}
```

### 2. Uso como Script CLI
Si solo necesitas el CSV sin la API:

```bash
python scraper.py --url "https://maps.app.goo.gl/..." --limit 50
```
Generará un archivo `reviews_<hash>.csv`.

---

## ☁️ Despliegue en Render

Este proyecto está optimizado para Render.

1.  Crear nuevo **Web Service**.
2.  Entorno: **Python 3**.
3.  Comando de Build:
    ```bash
    pip install -r requirements.txt && playwright install chromium
    ```
4.  Comando de Inicio:
    ```bash
    uvicorn api:app --host 0.0.0.0 --port $PORT
    ```
5.  **Variables de Entorno**:
    - `DATABASE_URL`: Tu conexión a PostgreSQL interna/externa de Render.

---

## ⚠️ Aviso Legal

Este software es una herramienta de prueba de concepto (PoC) con fines **educativos y de investigación académica**. 
- El scraping de sitios web puede violar los Términos de Servicio de Google.
- No utilice esta herramienta para extracción masiva no autorizada o comercial.
- El autor no se hace responsable del mal uso de este software.
