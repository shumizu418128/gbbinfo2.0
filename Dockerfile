# ベースイメージ
FROM python:3.9-slim

# アプリケーションの作業ディレクトリを設定
WORKDIR /app

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

EXPOSE 8080

# Redisサーバーを起動し、その後にFlaskアプリケーションを起動
CMD ["python", "run.py"]
