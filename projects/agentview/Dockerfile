FROM python:3.14-slim

WORKDIR /workspace

COPY . /workspace

RUN pip install --no-cache-dir fastapi uvicorn pillow python-multipart

ENV PYTHONPATH=/workspace/apps/api:/workspace

EXPOSE 7860

CMD ["uvicorn", "agentview_api.main:app", "--host", "0.0.0.0", "--port", "7860", "--app-dir", "apps/api"]
