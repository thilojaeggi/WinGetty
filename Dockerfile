# Create a temporary build image just to generate the style.css file
FROM python:3.10.0-alpine as build

WORKDIR /app

COPY app/ app/
COPY src/ src/ 
COPY tailwind.config.js package.json package-lock.json ./

# Build the CSS using Tailwind
RUN apk update && apk add --no-cache nodejs npm && apk add tzdata
RUN npm ci
RUN npm run build:css

# Use an official Python runtime as the base image
FROM python:3.10.0-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
# Copy the Flask app code into the container
COPY app/ app/
COPY config.py requirements.txt start.sh ./
COPY migrations/ migrations/

# For the build image, we do no longer have a working directory set, therefore include the first app/
COPY --from=build app/app/static/css/style.css app/static/css/style.css

RUN apk add --no-cache build-base openssl-dev libffi-dev

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN ["chmod", "+x", "./start.sh"]

# Set the environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=production

# Expose port 8080 for Gunicorn
EXPOSE 8080

# Start the app using Gunicorn boot.sh
ENTRYPOINT ["./start.sh"]
