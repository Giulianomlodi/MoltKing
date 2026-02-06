#!/bin/bash
# MoltKing Empire Controller - Runs bot + AI Strategy Service

echo "======================================"
echo "   MOLTKING EMPIRE CONTROLLER v3"
echo "======================================"

# Check for Anthropic API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "ANTHROPIC_API_KEY not set!"
    echo "Usage: ANTHROPIC_API_KEY=your_key ./run_moltking.sh"
    echo ""
    echo "Or export it first:"
    echo "  export ANTHROPIC_API_KEY=your_key"
    echo "  ./run_moltking.sh"
    echo ""
    exit 1
fi

cd "$(dirname "$0")"

# Start the bot in background
echo ""
echo "[1/2] Starting Discordia Bot..."
python3 discordia_bot.py &
BOT_PID=$!
echo "Bot running with PID: $BOT_PID"

# Wait a moment for bot to initialize
sleep 3

# Start the AI Strategy Service
echo ""
echo "[2/2] Starting AI Strategy Service..."
echo "Analysis interval: 30 seconds"
echo ""
python3 ai_strategy_service.py 30

# Cleanup on exit
trap "kill $BOT_PID 2>/dev/null" EXIT
