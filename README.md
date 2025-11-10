# Juffi - JSON Log Viewer

A feature-rich Terminal User Interface (TUI) for viewing and analyzing JSON log files with ease.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)

## Why Juffi?

JSON logs are powerful but painful to read in their raw format. Compare these two views of the same log data:

### Without Juffi
```json
{"timestamp":"2024-01-15T10:23:45.123Z","level":"INFO","message":"User login successful","user_id":"user_12345","ip":"192.168.1.100","session_id":"abc-def-ghi","service":"auth-service"}
{"timestamp":"2024-01-15T10:23:46.456Z","level":"WARN","message":"High memory usage detected","memory_percent":85.3,"process":"api-server","service":"monitoring"}
{"timestamp":"2024-01-15T10:23:47.789Z","level":"ERROR","message":"Database connection timeout","db_host":"db-primary.example.com","retry_count":3,"error":"connection timeout after 30s","service":"database"}
{"timestamp":"2024-01-15T10:23:48.012Z","level":"INFO","message":"API request received","method":"POST","path":"/api/v1/users","response_time_ms":45,"status_code":200,"service":"api-gateway"}
{"timestamp":"2024-01-15T10:23:49.234Z","level":"DEBUG","message":"Cache hit","cache_key":"user:12345:profile","ttl_seconds":3600,"service":"cache-service"}
{"timestamp":"2024-01-15T10:23:50.567Z","level":"INFO","message":"Payment processed","amount":99.99,"currency":"USD","transaction_id":"txn_abc123","user_id":"user_12345","service":"payment-service"}
{"timestamp":"2024-01-15T10:23:51.890Z","level":"WARN","message":"Rate limit approaching","current_requests":950,"limit":1000,"window_seconds":60,"ip":"192.168.1.100","service":"rate-limiter"}
{"timestamp":"2024-01-15T10:23:52.123Z","level":"ERROR","message":"Failed to send email","recipient":"user@example.com","error":"SMTP connection refused","retry_attempt":2,"service":"email-service"}
{"timestamp":"2024-01-15T10:23:53.456Z","level":"INFO","message":"File uploaded successfully","filename":"document.pdf","size_bytes":1048576,"user_id":"user_67890","service":"storage-service"}
{"timestamp":"2024-01-15T10:23:54.789Z","level":"DEBUG","message":"SQL query executed","query":"SELECT * FROM users WHERE id = ?","duration_ms":12,"rows_affected":1,"service":"database"}
{"timestamp":"2024-01-15T10:23:55.012Z","level":"INFO","message":"User logout","user_id":"user_12345","session_duration_seconds":1800,"service":"auth-service"}
{"timestamp":"2024-01-15T10:23:56.345Z","level":"WARN","message":"Slow query detected","query":"SELECT * FROM orders JOIN users","duration_ms":5000,"threshold_ms":1000,"service":"database"}
{"timestamp":"2024-01-15T10:23:57.678Z","level":"ERROR","message":"Authentication failed","user_id":"user_99999","reason":"invalid_credentials","ip":"10.0.0.50","service":"auth-service"}
{"timestamp":"2024-01-15T10:23:58.901Z","level":"INFO","message":"Background job completed","job_id":"job_456","job_type":"data_export","duration_seconds":120,"service":"worker"}
{"timestamp":"2024-01-15T10:23:59.234Z","level":"DEBUG","message":"WebSocket connection established","client_id":"ws_client_789","protocol":"wss","service":"websocket-server"}
{"timestamp":"2024-01-15T10:24:00.567Z","level":"INFO","message":"Metrics published","metric_count":150,"destination":"prometheus","service":"metrics-collector"}
{"timestamp":"2024-01-15T10:24:01.890Z","level":"WARN","message":"Disk space low","available_gb":5.2,"total_gb":100,"threshold_percent":10,"mount_point":"/data","service":"monitoring"}
{"timestamp":"2024-01-15T10:24:02.123Z","level":"ERROR","message":"External API timeout","api":"payment-gateway","endpoint":"/charge","timeout_seconds":30,"service":"integration"}
{"timestamp":"2024-01-15T10:24:03.456Z","level":"INFO","message":"Cache cleared","cache_type":"redis","keys_deleted":1500,"service":"cache-service"}
{"timestamp":"2024-01-15T10:24:04.789Z","level":"DEBUG","message":"Request validation passed","endpoint":"/api/v1/orders","validation_time_ms":5,"service":"api-gateway"}
{"timestamp":"2024-01-15T10:24:05.012Z","level":"INFO","message":"Scheduled task started","task_name":"daily_backup","schedule":"0 2 * * *","service":"scheduler"}
{"timestamp":"2024-01-15T10:24:06.345Z","level":"WARN","message":"Connection pool exhausted","pool_size":50,"active_connections":50,"waiting_requests":10,"service":"database"}
{"timestamp":"2024-01-15T10:24:07.678Z","level":"ERROR","message":"Message queue full","queue_name":"notifications","current_size":10000,"max_size":10000,"service":"message-queue"}
{"timestamp":"2024-01-15T10:24:08.901Z","level":"INFO","message":"Health check passed","endpoint":"/health","response_time_ms":2,"status":"healthy","service":"api-gateway"}
{"timestamp":"2024-01-15T10:24:09.234Z","level":"DEBUG","message":"Token refreshed","user_id":"user_12345","token_type":"JWT","expires_in_seconds":3600,"service":"auth-service"}
```

### With Juffi
<img width="980" height="542" alt="Juffi Browse View" src="https://github.com/user-attachments/assets/f8918239-6010-447d-8fad-f025eb813e80" />

## Features

### 🔍 Smart Log Viewing
- **Automatic column detection** - Juffi analyzes your JSON logs and creates columns for all fields
- **Tabular display** - View logs in a clean, organized table format
- **Details view** - Dive deep into individual log entries with full JSON expansion

### 📊 Powerful Filtering & Search
- **Column filtering** - Filter by any column to focus on relevant entries
- **Global search** - Search across all fields simultaneously
- **Clear filters** - Easily reset filters to start fresh

### 🎯 Column Management
- **Sortable columns** - Sort by any column (ascending or descending)
- **Reorderable columns** - Arrange columns in the order that makes sense to you
- **Adjustable widths** - Resize columns to fit your data
- **Column management screen** - Hide/show columns as needed

### 📡 Real-time Monitoring
- **Follow mode** - Like `tail -f`, automatically show new log entries as they're written
- **Live reload** - Refresh the view to pick up new entries
- **Responsive updates** - Smooth scrolling and navigation even with large files

<img width="693" height="831" alt="Juffi Help Screen" src="https://github.com/user-attachments/assets/074c7c21-3c4f-4b30-bad4-20601a4613f9" />

## Installation

### From PyPI (Recommended)
```bash
pip install juffi
```

### From Source
```bash
git clone https://github.com/YotamAlon/juffi.git
cd juffi
pip install -e .
```

## Quick Start

### Basic Usage
```bash
juffi app.log
```

## Requirements

- Python 3.11 or higher
- Terminal with curses support (most Unix-like systems)
- No external dependencies required

## Use Cases

Juffi is perfect for:
- **Debugging** - Quickly find errors and warnings in application logs
- **Monitoring** - Watch logs in real-time with follow mode
- **Analysis** - Sort and filter logs to identify patterns
- **Development** - Review structured logging output during development
- **Operations** - Investigate production issues with powerful search and filtering

## Technical Details

### Architecture
Juffi follows a clean MVVM (Model-View-ViewModel) architecture:
- **Models** (`juffi/models/`) - Data structures and business logic
- **ViewModels** (`juffi/viewmodels/`) - Presentation logic and state management
- **Views** (`juffi/views/`) - UI rendering using Python's curses library
- **Input Controller** (`juffi/input_controller.py`) - Handles file reading and input streaming

### Project Structure
```
juffi/
├── juffi/
│   ├── __main__.py           # Entry point
│   ├── input_controller.py   # File input handling
│   ├── models/               # Data models
│   ├── viewmodels/           # Presentation logic
│   ├── views/                # UI components
│   └── helpers/              # Utility functions
├── tests/                    # Test suite
├── pyproject.toml           # Project configuration
└── README.md
```

### Building from Source

#### Prerequisites
```bash
# Install development dependencies
pip install -e ".[dev]"
```

#### Build
```bash
# Build wheel and source distribution
make build

# Or building a wheel
make wheel
```

#### Testing
```bash
# Run tests
make test

# Run tests with coverage
make coverage

# Run linter
make lint
```

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YotamAlon/juffi.git
   cd juffi
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Code Quality
The project uses:
- **Black** - Code formatting
- **isort** - Import sorting
- **mypy** - Type checking
- **pylint** - Linting
- **pytest** - Testing

All checks run automatically via pre-commit hooks.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Author

**Yotam Alon** - [yotam.alon@gmail.com](mailto:yotam.alon@gmail.com)

## Links

- **Homepage**: https://github.com/YotamAlon/juffi
- **Issues**: https://github.com/YotamAlon/juffi/issues
- **PyPI**: https://pypi.org/project/juffi/
