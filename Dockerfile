FROM python:3.12-bookworm

# Create a non-root user
RUN useradd -ms /bin/bash appuser

RUN apt update && apt install -y --no-install-recommends \
    calibre \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/IBM/plex/releases/download/%40ibm%2Fplex-serif%401.1.0/ibm-plex-serif.zip \
    && unzip ibm-plex-serif.zip \
    && mv ibm-plex-serif/fonts/complete/otf/*.otf /usr/local/share/fonts/ \
    && rm -rf ibm-plex-serif/ ibm-plex-serif.zip

RUN wget https://github.com/IBM/plex/releases/download/%40ibm%2Fplex-sans%401.1.0/ibm-plex-sans.zip \
    && unzip ibm-plex-sans.zip \
    && mv ibm-plex-sans/fonts/complete/otf/*.otf /usr/local/share/fonts/ \
    && rm -rf ibm-plex-sans/ ibm-plex-sans.zip

RUN wget https://github.com/IBM/plex/releases/download/%40ibm%2Fplex-mono%401.1.0/ibm-plex-mono.zip \
    && unzip ibm-plex-mono.zip \
    && mv ibm-plex-mono/fonts/complete/otf/ /usr/local/share/fonts/ \
    && rm -rf ibm-plex-mono/ ibm-plex-mono.zip

RUN fc-cache -fv

WORKDIR /app
COPY requirements.txt /app
COPY templates/ /app/templates
COPY app.py /app/

# Set permissions for the non-root user
RUN chown -R appuser:appuser /app

RUN pip3 install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Switch to the non-root user
USER appuser

EXPOSE 80

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:80", "-w", "4", "--timeout", "300"]