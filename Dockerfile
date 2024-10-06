FROM python:3.9-slim

# create work folder and install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip wheel
RUN pip install --no-cache-dir -r requirements.txt

# copy the application code
COPY service/ ./service/

# create a non-root user and switch to it
RUN useradd -u 1000 theia && chown -R theia /app
USER theia

# run the service
EXPOSE 8080
CMD ["gunicorn", "--bind=0.0.0.0:8080", "--log-level=info", "service:app"]