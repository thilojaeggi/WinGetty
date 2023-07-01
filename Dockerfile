# Use an official Python runtime as the base image
FROM python:3.9-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

RUN apk add --no-cache build-base openssl-dev libffi-dev
# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app code into the container
COPY app/ app/
COPY tailwind.config.js .
COPY package.json .
COPY package-lock.json .
COPY src/ src/ 
COPY settings.toml .
COPY config.py .
COPY migrations/ migrations/
COPY boot.sh .

# Set the environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=production

# Build the CSS using Tailwind
RUN apk update && apk add --no-cache nodejs npm
RUN npm ci
RUN npm run build:css

# Create volumes for the 'instance' and 'packages' folders
VOLUME /app/instance
VOLUME /app/app/packages

# Expose port 8080 for Gunicorn
EXPOSE 8080

# Start the app using Gunicorn boot.sh
ENTRYPOINT ["./boot.sh"]
