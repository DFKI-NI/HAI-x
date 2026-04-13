FROM python:3.11
COPY . .
RUN pip install -r requirements.txt
EXPOSE 10002
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "10002"]