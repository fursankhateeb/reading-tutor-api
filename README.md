# Reading Tutor API - Cloud-Native Architecture

AI-powered bilingual reading tutor for children learning Arabic and English. Built with portable, scalable architecture to run anywhere: Replit, Railway, AWS, or local.

## 🏗️ Architecture Principles

This project follows **cloud-native, portable architecture**:

### ✅ What Makes This Portable

1. **Core Logic = Pure Python**
   - Zero external dependencies in `app/core/text_processor.py`
   - Uses only Python standard library
   - Works on any Python 3.7+ runtime
   - Can run in Lambda, Cloud Run, Railway, anywhere

2. **Swappable External Services**
   - Speech providers: Azure, Whisper, Riva (interface pattern)
   - Storage: Redis, Supabase, in-memory (abstract interface)
   - No vendor lock-in

3. **Thin API Layer**
   - Routes only handle HTTP concerns
   - All business logic in core/services layers
   - Easy to test and maintain

4. **Docker from Day One**
   - Multi-stage builds for optimization
   - Works on any container platform
   - Consistent across dev/prod environments

---

## 📁 Project Structure

```
reading-tutor/
├── app/
│   ├── core/                    # Pure business logic (no I/O)
│   │   ├── text_processor.py   # Reading correction algorithms
│   │   └── __init__.py
│   │
│   ├── services/                # External service interfaces
│   │   ├── speech_provider.py  # Abstract STT interface
│   │   ├── azure_speech.py     # Azure implementation
│   │   ├── storage.py          # Storage abstraction
│   │   └── __init__.py
│   │
│   ├── api/                     # Thin HTTP layer
│   │   ├── main.py             # FastAPI app
│   │   ├── models.py           # Pydantic schemas
│   │   ├── routes/
│   │   │   ├── reading.py      # Reading check endpoints
│   │   │   └── sessions.py     # Session management
│   │   └── __init__.py
│   │
│   └── config.py               # Environment-based config
│
├── tests/                       # Test suite
│   ├── test_core.py
│   ├── test_services.py
│   └── test_api.py
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── requirements.txt
├── .env.example
├── .gitignore
├── railway.json                 # Railway deployment config
└── README.md
```

---

## 🚀 Quick Start

### 1. Local Development (No Docker)

```bash
# Clone repo
git clone <your-repo>
cd reading-tutor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env  # Use memory storage and mock provider for quick start

# Run server
python -m uvicorn app.api.main:app --reload

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 2. Local Development (With Docker)

```bash
# Navigate to docker directory
cd docker

# Start all services (API + Redis)
docker-compose up

# API available at http://localhost:8000
# Redis Commander (GUI) at http://localhost:8081
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Check reading (English)
curl -X POST http://localhost:8000/api/v1/reading/check \
  -H "Content-Type: application/json" \
  -d '{
    "expected_sentence": "The cat sat on the mat",
    "speech_transcript": "The cat sat on the hat",
    "stt_confidence": 0.85
  }'

# Check reading (Arabic)
curl -X POST http://localhost:8000/api/v1/reading/check \
  -H "Content-Type: application/json" \
  -d '{
    "expected_sentence": "القطة تلعب في الحديقة",
    "speech_transcript": "القطة تلعب في البيت",
    "stt_confidence": 0.90,
    "language": "ar"
  }'
```

---

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available options. Key settings:

```bash
# Environment
ENVIRONMENT=development  # development, testing, production

# Speech Provider
SPEECH_PROVIDER=mock  # mock, azure, whisper, riva
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=eastus

# Storage
STORAGE_TYPE=memory  # memory, redis, supabase
REDIS_URL=redis://localhost:6379
```

### Development vs Production

**Development:**
```bash
ENVIRONMENT=development
STORAGE_TYPE=memory
SPEECH_PROVIDER=mock
DEBUG=true
```

**Production:**
```bash
ENVIRONMENT=production
STORAGE_TYPE=redis
REDIS_URL=${REDIS_URL}  # From Railway/Heroku
SPEECH_PROVIDER=azure
AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
DEBUG=false
```

---

## 🌐 Deployment

### Railway (Recommended)

1. **Connect GitHub:**
   - Push code to GitHub
   - Connect repo in Railway dashboard

2. **Add Environment Variables:**
   ```
   ENVIRONMENT=production
   STORAGE_TYPE=redis
   SPEECH_PROVIDER=azure
   AZURE_SPEECH_KEY=<your-key>
   AZURE_SPEECH_REGION=eastus
   ```

3. **Add Redis:**
   - Click "New" → "Database" → "Add Redis"
   - Railway automatically sets `REDIS_URL`

4. **Deploy:**
   - Railway auto-deploys on git push
   - Builds using `docker/Dockerfile`
   - Provides public URL

### Replit (For Testing)

1. Import GitHub repo to Replit
2. Create `.env` file with settings
3. Run: `python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000`

### Other Platforms

Works on:
- **Render**: Use Dockerfile, add Redis addon
- **Heroku**: Use Dockerfile, add Heroku Redis
- **AWS ECS**: Deploy Docker container
- **Google Cloud Run**: Deploy Docker container

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_core.py -v
```

---

## 📚 API Documentation

### Endpoints

#### `POST /api/v1/reading/check`
Check single reading and get feedback.

**Request:**
```json
{
  "expected_sentence": "The cat sat on the mat",
  "speech_transcript": "The cat sat on the hat",
  "stt_confidence": 0.85,
  "language": "en",
  "strict_mode": false,
  "include_metadata": false
}
```

**Response:**
```json
{
  "is_correct": false,
  "error_index": 5,
  "error_word": "mat",
  "feedback_type": "mispronounce",
  "language": "en"
}
```

#### `POST /api/v1/sessions/start`
Start a multi-sentence reading session.

#### `POST /api/v1/sessions/{session_id}/check-sentence`
Check current sentence in session.

#### `GET /api/v1/sessions/{session_id}/summary`
Get session statistics.

**Full documentation:** `http://localhost:8000/docs`

---

## 🔌 Adding Speech Providers

### Implement Custom Provider

```python
# app/services/my_provider.py
from app.services.speech_provider import BaseSpeechProvider, TranscriptionResult

class MyProvider(BaseSpeechProvider):
    async def transcribe(self, audio_data, language, expected_text):
        # Your STT implementation
        return TranscriptionResult(
            transcript="transcribed text",
            confidence=0.95,
            language=language,
            provider='my_provider'
        )
    
    async def assess_pronunciation(self, audio_data, expected_text, language):
        # Optional: pronunciation assessment
        pass
    
    def is_available(self):
        return True
```

### Register Provider

```python
# app/api/main.py
from app.services.my_provider import MyProvider
SpeechProviderFactory.register_provider('my_provider', MyProvider)
```

---

## 🎯 Key Features

### ✅ Bilingual Support
- English & Arabic
- Automatic language detection
- RTL text handling

### ✅ Arabic Diacritic Handling
- **Lenient Mode**: Ignores missing diacritics (learning phase)
- **Strict Mode**: Enforces diacritics (mastery phase)
- Configurable Hamza normalization

### ✅ Error Detection
- **Skip**: Child skipped a word
- **Mispronounce**: Said wrong word
- **Hesitation**: Low STT confidence
- **Success**: Read correctly

### ✅ Session Management
- Multi-sentence story tracking
- Progress monitoring
- Error history
- Accuracy statistics

---

## 🔒 Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Use Redis or Supabase (not in-memory storage)
- [ ] Configure real speech provider (not mock)
- [ ] Set strong secrets in environment variables
- [ ] Enable health check monitoring
- [ ] Set up logging/monitoring
- [ ] Configure CORS properly
- [ ] Enable HTTPS
- [ ] Set up backup/restore for Supabase

---

## 📈 Scaling Considerations

### Horizontal Scaling
✅ **Works out of the box:**
- Stateless API (no in-process state)
- Redis for shared session storage
- Can run multiple containers

### Performance
- Core logic is CPU-only (fast)
- No heavy ML models in container
- STT is external API call

### Cost Optimization
- **Development**: Use in-memory + mock ($0)
- **Small scale**: Railway + Redis ($5-20/month)
- **Medium scale**: Railway + Supabase ($20-50/month)
- **Large scale**: AWS ECS + ElastiCache (pay-as-you-go)

---

## 🤝 Contributing

1. Core logic is pure Python - keep it that way
2. External services must use interface pattern
3. API layer stays thin - business logic goes in core/services
4. All new features need tests
5. Document environment variables

---

## 📄 License

[Your License Here]

---

## 🆘 Support

- **Issues**: GitHub Issues
- **Docs**: `/docs` endpoint
- **Architecture**: This README

---

## 🎓 Next Steps

### Phase 1: MVP (Current)
- ✅ Core correction logic
- ✅ API with sessions
- ✅ Docker support
- ✅ Mock provider for testing

### Phase 2: Production
- [ ] Implement Azure Speech provider
- [ ] Add Whisper fallback
- [ ] Deploy to Railway
- [ ] Mobile app integration

### Phase 3: Advanced
- [ ] Phoneme-level feedback
- [ ] Progress tracking dashboard
- [ ] Multi-user support
- [ ] Analytics

---

Built with ❤️ for children learning to read
