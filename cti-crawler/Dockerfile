# Use ubuntu version 20.04
FROM ubuntu:20.04

# Update and install dependencies with interactive mode turned off (no need for user input)
RUN apt-get update && DEBIAN_FRONTEND="noninteractive" apt-get install -y \
    python3 python3-pip \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 \
    libnspr4 libnss3 lsb-release xdg-utils libxss1 libdbus-glib-1-2 libgbm1 \
    curl wget

# Set the working directory to /usr/src/app.
WORKDIR /app/crawler

# Add the working directory to env to ensure correct imports
ENV PYTHONPATH "/app/"

# Copy the project source code from the local host to the filesystem of the container at the working directory.
COPY . .

# Install Google Chrome

RUN CHROME_SETUP=google-chrome.deb && \
    wget -O $CHROME_SETUP "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" && \
    dpkg -i $CHROME_SETUP && \
    apt-get install -y -f && \
    rm $CHROME_SETUP

# Install dependencies specified in requirements.txt.
RUN pip3 install --no-cache-dir -r requirements.txt

