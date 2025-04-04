#!/bin/bash
# setup4host.sh - set up virtual environment, install dependencies and create systemd file

program_name="updatefetch"   # 不能有空格等特殊符号
current_uid=$(id -u)
current_dir=$(pwd)

# 确保存在虚拟环境并安装包
if [ ! -d .env ]
then
    python3 -m venv .env
fi
source .env/bin/activate
pip install -r requirements.txt

# 配置文件。若不存在 config_and_data_files 就自动复制示例配置文件，否则不操作
if [ ! -d config_and_data_files ]
then
    mkdir config_and_data_files && \
    cp examples/config.yaml config_and_data_files/config.yaml && \
    cp examples/pgm_config.yaml config_and_data_files/pgm_config.yaml && \
    cp examples/items.yaml config_and_data_files/items.yaml
fi
mkdir -p temp_download

# 创建 systemd 配置文件
if [ ! -d ${program_name}.service ]
then
cat > ./${program_name}.service <<EOF
[Unit]
Description=${program_name} Service
After=network.target

[Service]
WorkingDirectory=${current_dir}
User=${current_uid}
Group=${current_uid}
Type=simple
ExecStart=${current_dir}/.env/bin/uvicorn main:app --host 0.0.0.0 --port 8679
ExecStop=/bin/kill -s HUP $MAINPID
Environment=PYTHONUNBUFFERED=1
RestartSec=15
Restart=on-failure

[Install]
WantedBy=default.target
EOF
fi


# vim: expandtab shiftwidth=4 softtabstop=4