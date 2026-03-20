# Windows 复现与启动操作文档

本文档用于在另一台 Windows 电脑上复现并启动本项目。

默认约定：

- 项目根目录示例：`D:\222毕设`
- 后端虚拟环境：`.venv`
- Flink 虚拟环境：`.venv_flink`
- Docker 离线镜像包：`docker_images_offline.tar`

如果你的实际目录不同，把下面命令里的 `D:\222毕设` 替换成你自己的路径即可。

## 1. 环境准备

需要提前安装：

- Python 3.11
- Docker Desktop
- JDK 17

检查命令：

```powershell
python --version
docker version
java -version
```

## 2. 项目目录确认

项目根目录应至少包含这些目录和文件：

- `apps`
- `services`
- `infra`
- `docs`
- `tests`
- `offline_wheels`
- `docker_images_offline.tar`

进入项目目录：

```powershell
cd "D:\222毕设"
```

## 3. 导入 Docker 离线镜像

如果这台电脑无法访问 Docker Hub，先导入离线镜像：

```powershell
cd "D:\222毕设"
docker load -i ".\docker_images_offline.tar"
```

## 4. 创建虚拟环境

### 4.1 创建后端环境

```powershell
cd "D:\222毕设"
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-core.txt
```

### 4.2 创建 Flink 环境

```powershell
cd "D:\222毕设"
py -3.11 -m venv .venv_flink
& ".\.venv_flink\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv_flink\Scripts\python.exe" -m pip install apache-flink==1.20.0 kafka-python==2.0.2
```

## 5. Java 检查

Flink 启动前，先确认 Java 可用：

```powershell
java -version
where.exe java
```

如果 `java -version` 报错，说明 JDK 17 没有配置好。可以临时设置：

```powershell
$env:JAVA_HOME="C:\Program Files\Java\jdk-17"
$env:Path="$env:JAVA_HOME\bin;$env:Path"
java -version
```

如果确认目录无误，可以再把 `JAVA_HOME` 和 `%JAVA_HOME%\bin` 写入系统环境变量。

## 6. 完整启动顺序

建议开 4 个 PowerShell 窗口，按顺序执行。

### 终端 1：启动基础组件

```powershell
cd "D:\222毕设\infra"
docker compose up -d
```

可选检查：

```powershell
docker compose ps
```

### 终端 2：启动后端

```powershell
cd "D:\222毕设"
& ".\.venv\Scripts\python.exe" ".\apps\backend\run.py"
```

后端启动后，浏览器可访问：

```text
http://127.0.0.1:5000
```

### 终端 3：启动采集器

```powershell
cd "D:\222毕设"
.\start_collectors.ps1 -PythonPath ".\.venv\Scripts\python.exe"
```

说明：

- 脚本会自动拉起 `live_001`、`live_002`、`live_003` 三个采集窗口
- 当前采集器是模拟事件流，不是真实抖音直播抓取

### 终端 4：启动 Flink 实时任务

```powershell
cd "D:\222毕设"
& ".\.venv_flink\Scripts\python.exe" ".\services\flink_job\realtime_metrics.py" --bootstrap localhost:9092 --topic live_events --metrics-topic live_metrics --window-seconds 10
```

正常情况下，终端会打印类似：

```text
[flink] pipeline.jars=...
```

只要没有继续报错，这个窗口就保持运行，不要关闭。

## 7. 前端查看方式

打开浏览器：

```text
http://127.0.0.1:5000
```

进入“数据”页后：

1. 选择直播间 `live_001`、`live_002` 或 `live_003`
2. 点击“开启实时”
3. 观察在线人数、互动趋势、漏斗图和情感图是否变化

## 8. 快速检查命令

### 8.1 后端健康检查

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

正常返回：

```json
{"status":"ok"}
```

### 8.2 重置后端演示数据

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:5000/api/bootstrap
```

### 8.3 检查 Python 可执行文件

```powershell
cd "D:\222毕设"
Get-ChildItem .\.venv\Scripts\python*.exe, .\.venv_flink\Scripts\python*.exe -ErrorAction SilentlyContinue
```

## 9. 停止项目

### 停止采集器

```powershell
cd "D:\222毕设"
.\stop_collectors.ps1
```

### 停止 Docker 基础组件

```powershell
cd "D:\222毕设\infra"
docker compose down
```

### 停止后端和 Flink

在各自运行窗口直接按：

```text
Ctrl + C
```

## 10. 常见问题

### 10.1 找不到 `.venv_flink\Scripts\python.exe`

说明 `.venv_flink` 没创建成功或路径不对。重新执行：

```powershell
cd "D:\222毕设"
py -3.11 -m venv .venv_flink
```

### 10.2 Flink 报 `FileNotFoundError: [WinError 2]`

高概率是 Java 没装好或 `java` 不在 `Path` 里。先执行：

```powershell
java -version
where.exe java
```

### 10.3 采集器报 `KafkaTimeoutError`

说明 Kafka 还没起来，先检查：

```powershell
cd "D:\222毕设\infra"
docker compose ps
```

### 10.4 前端打开了，但数据不动

检查是否同时满足：

- 后端已启动
- 采集器已启动
- Flink 已启动
- 前端已点击“开启实时”

### 10.5 只有一个直播间有数据

建议统一使用：

```powershell
.\start_collectors.ps1 -PythonPath ".\.venv\Scripts\python.exe"
```

不要手动只开一个 `collector.py` 进程。

## 11. 当前项目实际启动命令汇总

```powershell
cd "D:\222毕设\infra"
docker compose up -d
```

```powershell
cd "D:\222毕设"
& ".\.venv\Scripts\python.exe" ".\apps\backend\run.py"
```

```powershell
cd "D:\222毕设"
.\start_collectors.ps1 -PythonPath ".\.venv\Scripts\python.exe"
```

```powershell
cd "D:\222毕设"
& ".\.venv_flink\Scripts\python.exe" ".\services\flink_job\realtime_metrics.py" --bootstrap localhost:9092 --topic live_events --metrics-topic live_metrics --window-seconds 10
```
