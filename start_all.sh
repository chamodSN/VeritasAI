#!/bin/bash

echo "Starting all VeritasAI agents..."

# Query Parsing + Search (port 8001)
uvicorn agents.case_finder.main:app --port 8001 --reload --log-level info &
PID1=$!

# Summary (port 8002)
uvicorn agents.summary.main:app --port 8002 --reload --log-level info &
PID2=$!

# Citation (port 8003)
uvicorn agents.citation.citation:app --port 8003 --reload --log-level info &
PID3=$!

# Precedent (port 8004)
uvicorn agents.precedent.main:app --port 8004 --reload --log-level info &
PID4=$!

# Orchestrator (port 8000)
uvicorn orchestrator.main:app --port 8000 --reload --log-level info &
PID5=$!

echo "All agents started. PIDs: $PID1, $PID2, $PID3, $PID4, $PID5"
echo "Press Ctrl+C to stop all agents..."

# Trap Ctrl+C to kill all processes
trap "echo 'Stopping all agents...'; kill $PID1 $PID2 $PID3 $PID4 $PID5; exit" SIGINT

# Wait for all processes to finish
wait