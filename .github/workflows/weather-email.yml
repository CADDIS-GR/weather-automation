name: Send Weather Email

on:
  schedule:
    - cron: '0 22 * * *'  # 매일 오전 7시 (한국시간)
  workflow_dispatch:

jobs:
  send-weather-email:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          pip install requests
          
      - name: Send weather email
        env:
          SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}
          SENDER_PASSWORD: ${{ secrets.SENDER_PASSWORD }}
          RECEIVER_EMAIL: ${{ secrets.RECEIVER_EMAIL }}
        run: |
          python send_weather_email.py
