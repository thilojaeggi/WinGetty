FROM python:3.11.4
ADD . /app
WORKDIR /app
RUN apt-get update && \
    apt-get install -y npm && \
    npm install && \
    npm run build:css
RUN pip install -r requirements.txt
EXPOSE 80
CMD ["gunicorn", "-b", "0.0.0.0:80", "--workers", "2", "app:create_app()"]