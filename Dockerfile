# Use the official Ubuntu 22.04 LTS base image
FROM ubuntu:22.04

# Set noninteractive mode
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
    apt-get install -y git curl build-essential libssl-dev zlib1g-dev libbz2-dev \
                       libreadline-dev libsqlite3-dev wget llvm libncurses5-dev libncursesw5-dev \
                       xz-utils tk-dev libffi-dev liblzma-dev python3-openssl python3-pip git

# Update pip
RUN python3 -m pip install --upgrade pip setuptools

# Clone the repository
RUN git clone https://github.com/udea-telematics-telegods-2023-2/bank_server.git /app

# Change working directory
WORKDIR /app

# Install poetry via pip
RUN python3 -m pip install poetry

# Use Python 3.10
RUN poetry env use 3.10

# Install project dependencies
RUN poetry install --no-root

# Generate a self-signed SSL certificate
RUN mkdir credentials

# Set the command to run your application
CMD ["poetry", "run", "python", "-m", "src.server"]
