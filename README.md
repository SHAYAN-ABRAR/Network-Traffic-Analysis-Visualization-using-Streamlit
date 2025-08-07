# Network Traffic Visualization Dashboard

## Overview

This Streamlit application visualizes network traffic data from syslog, offering real-time insights into IP and port activity. Integrated with a CRM/self-service portal via MySQL, it provides interactive scatter plots, bar charts, and pie charts for efficient monitoring and analysis.

## Features

- **Customizable Date Selection**: Analyze data from the past 10 days.
- **IP Scatter Plot**: Visualize destination IP vs. port counts.
- **Port and Domain Charts**:
  - Bar chart for top 20 destination ports.
  - Pie chart for domain hit percentages.
- **Yellow and Black Theme**: Modern, high-contrast UI with Plotly visualizations.
- **Database Integration**: Connects to MySQL for real-time syslog data retrieval.
- **API Integration**: Uses ipinfo.io for domain and IP metadata.

## Requirements

- **Python 3.8+**
- **Streamlit**
- **Pandas**
- **MySQL Connector**
- **Plotly**
- **Requests**
- **MySQL database with syslog schema**
- **ipinfo.io API token**

- To run in terminal, use this: streamlit run "e:/Network Traffic Analysis Visualization using Streamlit/Network Traffic AnalysisWithPlot.py"
