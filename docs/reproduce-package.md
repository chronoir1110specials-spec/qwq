# 复现打包说明

这份项目在另一台 Windows 电脑上复现时，建议按下面两档来打包。

## 1. 默认源码复现包

适合另一台电脑可以联网安装 Python 依赖，或者你已经准备好了本项目的 `offline_wheels`。

建议至少包含：

- `apps`
- `services`
- `infra`
- `docs`
- `tests`
- `爬取`
- `offline_wheels`
- `data/system.db`
- `requirements-core.txt`
- `requirements-pipeline.txt`
- `run_system.ps1`
- `start_collectors.ps1`
- `stop_collectors.ps1`
- `download_wheels.ps1`

默认不建议打包：

- `.git`
- `.idea`
- `.pytest_cache`
- `.venv`
- `.venv311`
- `data/raw_events.jsonl`

原因：

- 虚拟环境通常和当前机器路径、解释器位置强绑定，直接拷到另一台电脑经常不可用。
- `raw_events.jsonl` 属于当前机器运行产生的临时数据，带过去会混入旧采集结果。

## 2. 离线完整复现包

如果另一台电脑无法联网，除了源码复现包，建议额外带上：

- `docker_images_offline.tar`
- `offline_wheels`

这样可以离线导入 Docker 镜像，并离线安装 Python 依赖。

## 3. 另一台电脑的前置要求

- Windows 10/11
- Python 3.11
- Node.js
- Docker Desktop
- JDK 17

其中网页直播采集功能依赖 Node.js 或 `mini-racer` 来计算签名。当前项目已经优先走 Node.js。

## 4. 推荐启动顺序

如果你不是从压缩包解压，而是直接从 GitHub 克隆，请用：

```powershell
git clone --recurse-submodules <your-repo-url>
```

如果你已经克隆过了，再补一次：

```powershell
git submodule update --init --recursive
```

1. 创建虚拟环境并安装依赖

```powershell
cd D:\抖音数据分析系统
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r .\requirements-core.txt
```

如果离线安装：

```powershell
cd D:\抖音数据分析系统
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --no-index --find-links .\offline_wheels -r .\requirements-core.txt
```

2. 启动后端

```powershell
cd D:\抖音数据分析系统
& .\.venv\Scripts\python.exe .\apps\backend\run.py
```

3. 打开页面

```text
http://127.0.0.1:5000
```

4. 如果要使用网页直播采集

- 在“数据”页输入 `Web RID`
- 可选输入 `主播 ID`
- 先点“查询直播状态”
- 再点“启动网页采集”

## 5. 自动打包

项目根目录新增了 `package_release.ps1`，可以自动生成源码复现包 zip。

默认打包：

```powershell
cd D:\抖音数据分析系统
.\package_release.ps1
```

如果你还想把 `docker_images_offline.tar` 一起塞进包里：

```powershell
cd D:\抖音数据分析系统
.\package_release.ps1 -IncludeDockerImages
```
