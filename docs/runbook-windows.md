# 鎶栭煶鐩存挱鏁版嵁鍒嗘瀽绯荤粺杩愯鎵嬪唽锛圵indows锛?
## 1. 閫傜敤鑼冨洿

鏈墜鍐岀敤浜庡湪 Windows 鐜涓嬶紝浠庨浂鍚姩骞惰繍琛屾湰椤圭洰锛?
- 鐪嬫澘灞曠ず閾捐矾锛欶lask API + SQLite 鏍蜂緥鏁版嵁 + ECharts 鍓嶇
- 鏁版嵁澶勭悊閾捐矾锛堝彲閫夛級锛欳ollector -> Kafka -> Flink / Spark

椤圭洰鏍圭洰褰曪細`D:\lzy姣曡`

---

## 2. 棣栨鐜鍑嗗

鍦?PowerShell 涓墽琛岋細

```powershell
cd D:\lzy姣曡
py -3 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-core.txt
```

濡傛灉浣犺璺?Kafka / Spark / Flink 鐩稿叧妯″潡锛屽啀鎵ц锛?
```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-pipeline.txt
```

---

## 3. 蹇€熷惎鍔紙鎺ㄨ崘锛?
杩欐槸鏈€灏忓彲杩愯璺緞锛岀洿鎺ョ湅鍒扮郴缁熺晫闈細

```powershell
cd D:\lzy姣曡
& ".\.venv\Scripts\python.exe" ".\apps\backend\run.py"
```

娴忚鍣ㄨ闂細

`http://127.0.0.1:5000`

---

## 4. 鍚姩鍚庢鏌?
鍋ュ悍妫€鏌ワ細

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

鏈熸湜杩斿洖锛?
```json
{"status":"ok"}
```

閲嶇疆婕旂ず鏁版嵁锛堝彲閫夛級锛?
```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:5000/api/bootstrap
```

---

## 5. 瀹屾暣鏁版嵁閾捐矾锛堝彲閫夛級

### 5.1 鍚姩鍩虹缁勪欢

```powershell
cd D:\lzy姣曡\infra
docker compose up -d
```

### 5.2 鍚姩閲囬泦鍣?
```powershell
cd D:\lzy姣曡
& ".\.venv\Scripts\python.exe" ".\services\collector\collector.py" --bootstrap localhost:9092 --topic live_events --live-id live_001 --interval 1
```

### 5.3 璺?Spark 绂荤嚎浠诲姟

```powershell
cd D:\lzy姣曡
& ".\.venv\Scripts\python.exe" ".\services\spark_job\offline_metrics.py" --input data\raw_events.jsonl --output data\dws
```

### 5.4 杩愯 Flink 瀹炴椂浠诲姟锛圵indows 鍙窇锛屼絾鏇村缓璁?Linux/WSL锛?
```powershell
cd D:\lzy姣曡
& ".\.venv\Scripts\python.exe" ".\services\flink_job\realtime_metrics.py" --bootstrap localhost:9092 --topic live_events --output file:///D:/lzy姣曡/data/realtime_metrics
```

璇存槑锛?
- 闇€瑕佹湰鍦?Flink 鐜鍜?Kafka Connector JAR锛堢増鏈尮閰嶏級銆?- 濡傛姤閿?`Cannot discover connector 'kafka'`锛岄€氬父鏄?connector 鏈斁鍒?Flink `lib` 鎴栫増鏈笉鍖归厤銆?
### 5.5 鍋滄鍩虹缁勪欢

```powershell
cd D:\lzy姣曡\infra
docker compose down
```

---

## 6. 甯歌闂鎺掓煡

### 6.1 鎵句笉鍒?`.venv\Scripts\python.exe`

鎵ц锛?
```powershell
cd D:\lzy姣曡
Get-ChildItem .\.venv\Scripts\python*.exe
```

鑻ユ棤缁撴灉锛岄噸寤鸿櫄鎷熺幆澧冿細

```powershell
py -3 -m venv .venv
```

### 6.2 PowerShell 婵€娲昏剼鏈绛栫暐鎷︽埅

涓嶈鐢?`Activate.ps1`锛岀洿鎺ョ敤锛?
```powershell
& ".\.venv\Scripts\python.exe" <浣犵殑鑴氭湰璺緞>
```

### 6.3 `ModuleNotFoundError: flask`

鎵ц锛?
```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-core.txt
```

### 6.4 5000 绔彛琚崰鐢?
鏌ュ崰鐢細

```powershell
netstat -ano | findstr :5000
```

缁撴潫杩涚▼锛?
```powershell
taskkill /PID <PID> /F
```

### 6.5 pip 涓嬭浇澶辫触锛堢綉缁?璇佷功锛?
浣跨敤娓呭崕闀滃儚锛?
```powershell
& ".\.venv\Scripts\python.exe" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements-core.txt
& ".\.venv\Scripts\python.exe" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements-pipeline.txt
```

### 6.6 椤甸潰鎵撳紑浣嗗浘琛ㄦ棤鏁版嵁/鎶ラ敊

鎸夐『搴忔墽琛岋細

1. 鍏堢‘璁ゅ仴搴锋鏌ワ細`/api/health` 鏄惁姝ｅ父  
2. 鎵ц涓€娆?`/api/bootstrap` 閲嶇疆鏍蜂緥鏁版嵁  
3. 鑻ヤ粛寮傚父锛屽垹闄?`data\system.db` 鍚庨噸鍚悗绔?
---

## 7. 甯哥敤鍛戒护閫熸煡

鍚姩绯荤粺锛?
```powershell
cd D:\lzy姣曡
& ".\.venv\Scripts\python.exe" ".\apps\backend\run.py"
```

杩愯娴嬭瘯锛?
```powershell
cd D:\lzy姣曡
& ".\.venv\Scripts\python.exe" -m pytest -q
```

涓嬭浇绂荤嚎鍖咃細

```powershell
cd D:\lzy姣曡
pip download -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn -r requirements-core.txt -r requirements-pipeline.txt -d .\offline_wheels
```
