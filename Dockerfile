FROM python:3.11.4
ADD . /app
WORKDIR /app
RUN apt-get update && \
    apt-get install -y npm && \
    npm ci && \
    npm run build:css && \
    apt-get remove -y npm && \
    rm -rf node_modules
RUN pip install -r requirements.txt
EXPOSE 80
CMD ["gunicorn", "-b", "0.0.0.0:80", "--workers", "2", "app:create_app()"]