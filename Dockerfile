# ベースイメージ
FROM python:3.9-slim

# Redisのインストール
RUN apt-get update && \
    apt-get install -y redis-server

# Redisの設定ファイルをコピー
COPY redis.conf /usr/local/etc/redis/redis.conf

# アプリケーションの作業ディレクトリを設定
WORKDIR /app

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# コンテナ内のディレクトリ構造を確認（オプション）
RUN ls -l /app/app

# Redisサーバーを起動し、その後にFlaskアプリケーションを起動
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"] && python run.py
