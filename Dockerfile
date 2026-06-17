FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CHRONOS_ENV=production
ENV CHRONOS_DB_PATH=~/.chronos/chronos.db

RUN pip install -e .

EXPOSE 5000

CMD ["chronos", "serve"]
