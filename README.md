# EchoCloset

## 這邊是夜芷冰寫的部分
【一個小實驗】這是一個由AI自己想出來的Discord bot，所有原始碼均是由它一人完成，我僅作爲提議者
如果你有興趣的話，可以看看chat.json,裏面記錄了我和它的對話過程
好了，下面是它寫的README.md內容

## 介紹
EchoCloset是一個Discord機器人，幫助用戶記錄每日心情和想買的東西，並進行情感分析。它結合了關鍵詞匹配和Transformers模型來識別情緒，並提供簡單的購物囤物管理功能。

## 功能
- `/echo <內容>`: 記錄一句話，自動提取情緒標籤（詞庫 + Transformers）。
- `/recent [count] [days]`: 查看最近記錄。
- `/analyze`: 分析最近一個月常見情緒詞。
- `/hoard <描述> [冷靜期天數]`: 記錄想買的東西，預設7天冷靜期。
- `/hoard_list`: 查看待處理的囤物清單。
- `/toggle_ghost`: 切換鬼魂模式（只在凌晨2:30-5:00正常回應）。
- `/obliterate` & `/obliterate_confirm`: 刪除所有記錄。

## 安裝
1. `pip install -r requirements.txt`
2. 創建`.env`檔案，放`TOKEN=你的Discord機器人TOKEN`
3. `python echo_closet.py` （第一次運行會下載模型，較慢）

## 情感分析
- 詞庫匹配：手動定義關鍵詞（快樂、悲傷、生氣、焦慮、疲憊、震驚、懼怕、疑惑）。
- Transformers：多語言情感模型（1-5星映射到正面/負面），使用GPU加速。
