pip install -r test/requirements.txt
playwright install
pytest test/test_backend.py
python test/test_frontend.py