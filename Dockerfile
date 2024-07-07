FROM minizinc/minizinc:latest

# Install linux packages
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    python3 \
    python3-pip \
    build-essential \
    libpq-dev \
    glpk-utils \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /src

COPY . .

RUN python3 -m pip install -r requirements.txt --break-system-packages

# What to run when the container starts
CMD ["./run_all.sh", "--verbose"]