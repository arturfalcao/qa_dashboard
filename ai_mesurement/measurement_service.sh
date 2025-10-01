#!/bin/bash
# Measurement service startup script

cd /home/celso/projects/qa_dashboard/ai_mesurement

# Activate virtual environment
source venv/bin/activate

# Run the measurement integration service
python qa_dashboard_integration.py --continuous