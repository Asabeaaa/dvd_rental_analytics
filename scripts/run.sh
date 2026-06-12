#!/usr/bin/env bash
set -e

python 1_setup_validate.py
python 2_data_exploration.py
python 3_data_relationships.py
python 4_analysis.py
streamlit run 5_dashboard.py