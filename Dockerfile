# ベースイメージ
FROM python:3.12-slim

ENV TZ=Asia/Tokyo
RUN apt-get update && apt-get install -y tzdata

# uvをインストール
RUN pip install uv

# アプリケーションの作業ディレクトリを設定
WORKDIR /app

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN uv pip install -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

EXPOSE 8080

# Redisサーバーを起動し、その後にFlaskアプリケーションを起動
CMD ["python", "run.py"]
