#!/bin/bash
# Start script for Cathode
# Uses Python 3.10 (required for Kokoro TTS)

PYTHON="/opt/homebrew/bin/python3.10"

# Check if Python 3.10 exists
if [ ! -f "$PYTHON" ]; then
    echo "Error: Python 3.10 not found at $PYTHON"
    echo "Install with: brew install python@3.10"
    exit 1
fi

# Check for required packages
$PYTHON -c "import streamlit, kokoro, anthropic, openai, replicate" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Missing dependencies. Installing..."
    $PYTHON -m pip install -r requirements.txt
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the app
PORT="${STREAMLIT_PORT:-8517}"
echo "Starting Cathode..."
echo "Opening http://localhost:${PORT}"
$PYTHON -m streamlit run app.py --server.port "${PORT}" "$@"
