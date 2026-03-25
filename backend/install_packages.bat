@echo off
echo Installing ARAQAT backend dependencies...
echo.
call venv\Scripts\activate.bat
pip install python-docx==1.1.2 fpdf2==2.7.9
echo.
echo Done! Now restart the Flask server: python app.py
pause
