FROM python:3.11-slim

RUN useradd --create-home --uid 1000 user
WORKDIR /home/user/app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

USER user
ENV PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/user/.cache/huggingface \
    WW_CACHE_DIR=/home/user/.cache/huggingface \
    WW_DATA_DIR=/tmp/weather-whiplash

COPY --chown=user backend/app ./app
COPY --chown=user backend/samples ./samples

# Bake the pinned model into the image. A restarted free Space therefore does not need
# to download weights before it can answer its first health check.
RUN python -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32', cache_dir='/home/user/.cache/huggingface'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32', cache_dir='/home/user/.cache/huggingface')"

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
