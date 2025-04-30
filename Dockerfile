FROM python:3.7-slim

# 安装系统依赖（如果需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# 拷贝代码
WORKDIR /app
COPY . /app

# 安装 pip 依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
