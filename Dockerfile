FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN g++ -O3 -std=c++17 -Wall -Wextra cpp/map_engine.cpp -o cpp/map_engine \
    && chmod +x cpp/map_engine \
    && python -m py_compile gridloop_service.py main.py career.py showrunner.py metadata.py

CMD ["python", "gridloop_service.py"]
