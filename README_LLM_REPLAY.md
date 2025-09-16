# LLM Replay System

A comprehensive system for managing, executing, and analyzing LLM test cases with replay functionality.

## 🚀 Features

- **Test Case Management**: Create, edit, and organize LLM test cases from logfire raw data
- **Intelligent Parsing**: Automatically parse logfire data and separate system prompts, user messages, and other components
- **Replay Execution**: Execute tests with original or modified parameters using pydantic-ai Direct Model Requests
- **Execution Logging**: Track all test executions with detailed logs and performance metrics
- **Web Interface**: User-friendly web interface for all operations
- **REST API**: Complete REST API for programmatic access

## 🏗️ Architecture

The system follows a layered architecture:

```
┌─────────────────┐
│   Frontend      │  Bootstrap + JavaScript
├─────────────────┤
│   API Layer     │  FastAPI REST endpoints
├─────────────────┤
│ Business Logic  │  Services (TestCase, Execution, Logs)
├─────────────────┤
│   Data Layer    │  SQLAlchemy models + stores
├─────────────────┤
│   Database      │  PostgreSQL
└─────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL database
- Redis (for caching)
- pydantic-ai framework
- OpenRouter API access (for LLM calls)

## 🛠️ Installation

1. **Clone the repository** (if not already done)

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your database and API credentials
   ```

4. **Initialize the database**:
   ```bash
   python scripts/init_database.py
   ```

5. **Run system tests**:
   ```bash
   python scripts/test_system.py
   ```

## 🚀 Quick Start

### 1. Start the Server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Access the Web Interface

Open your browser and navigate to:
- **Home/Test Cases**: http://localhost:8000/
- **Test Execution**: http://localhost:8000/test-execution
- **Test Logs**: http://localhost:8000/test-logs

### 3. Create Your First Test Case

1. Go to the Test Cases page
2. Click "Create Test Case"
3. Enter a name and description
4. Paste your logfire raw data JSON
5. Click "Create Test Case"

The system will automatically parse the raw data and extract:
- System prompt
- User message  
- Other messages
- Tools
- Model information

### 4. Execute Tests

1. Go to the Test Execution page
2. Select a test case from the dropdown
3. Optionally modify the system prompt, user message, or model
4. Click "Execute Test"
5. View the results in real-time

### 5. View Test Logs

1. Go to the Test Logs page
2. Filter by status, test case, or view all logs
3. Click on any log to view detailed execution information
4. Re-execute tests directly from the logs

## 🔧 API Usage

### Test Cases

```bash
# Create test case
curl -X POST "http://localhost:8000/v1/api/test-cases/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Case",
    "description": "Test description",
    "raw_data": {...}
  }'

# Get all test cases
curl "http://localhost:8000/v1/api/test-cases/"

# Get specific test case
curl "http://localhost:8000/v1/api/test-cases/{test_case_id}"

# Update test case
curl -X PUT "http://localhost:8000/v1/api/test-cases/{test_case_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "parsed_system_prompt": "Updated prompt"
  }'

# Delete test case
curl -X DELETE "http://localhost:8000/v1/api/test-cases/{test_case_id}"
```

### Test Execution

```bash
# Execute test
curl -X POST "http://localhost:8000/v1/api/test-execution/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_id": "test-case-id",
    "model_name": "openrouter:anthropic/claude-sonnet-4",
    "system_prompt": "Custom system prompt",
    "user_message": "Custom user message"
  }'

# Get execution preview
curl "http://localhost:8000/v1/api/test-execution/preview/{test_case_id}"
```

### Test Logs

```bash
# Get all logs
curl "http://localhost:8000/v1/api/test-logs/"

# Get logs by test case
curl "http://localhost:8000/v1/api/test-logs/test-case/{test_case_id}"

# Get logs by status
curl "http://localhost:8000/v1/api/test-logs/status/success"
curl "http://localhost:8000/v1/api/test-logs/status/failed"

# Get specific log
curl "http://localhost:8000/v1/api/test-logs/{log_id}"
```

## 🔄 Replay Mechanism

The system implements an optimized replay strategy:

1. **Data Separation**: Raw data is parsed to separate:
   - System prompt (first system message)
   - User message (last user message)  
   - Other messages (everything else)
   - Tools and model information

2. **Replay Concatenation**: During execution:
   ```
   Final Messages = [System Prompt] + [Other Messages] + [User Message]
   ```

3. **Modification Support**: Users can modify system prompt and user message while preserving the original conversation flow.

## 📊 Data Models

### TestCase
- Stores original raw data for audit
- Separated components for easy modification
- Metadata and timestamps

### TestLog  
- Complete execution record
- Performance metrics
- Success/failure status
- Full LLM response

## 🛡️ Error Handling

The system includes comprehensive error handling:
- Input validation
- Database transaction safety
- LLM call error recovery
- User-friendly error messages

## 🧪 Testing

Run the integration tests:

```bash
# Full system test
python scripts/test_system.py

# Reset database (development only)
python scripts/reset_database.py
```

## 📝 Configuration

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/replay_llm_call

# Redis
REDIS_URL=redis://localhost:6379

# API Keys
OPENROUTER_API_KEY=your_api_key_here

# Logging
LOG_LEVEL=INFO
```

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Use the established patterns for services and stores

## 📄 License

This project is part of the replay-llm-call system.

---

## 🎯 Next Steps

- Add more LLM providers
- Implement batch execution
- Add test case templates
- Enhanced analytics and reporting
- Export/import functionality
