# echo_closet.py
# 極早期雛形 - 殘響櫃 v0.0.1-alpha
# 需要: pip install discord.py

import discord
from discord import app_commands
import datetime
import json
import os
from typing import Optional, List
import jieba
from dotenv import load_dotenv
import asyncio
from transformers import pipeline

# ------------------ 設定 ------------------
load_dotenv()
TOKEN = os.getenv("TOKEN")           # 記得放 .env 或其他方式管理
DATA_FILE = "echo_closet_records.json"  # 簡單用 json 存，之後再換資料庫

ghost_mode = False  # 鬼魂模式：只在凌晨回應

# 簡單情緒詞列表（可擴充）
EMOTION_WORDS = {
    "快樂": ["開心", "歡樂", "興奮", "愉快", "高興", "快樂", "樂", "爽", "好玩", "有趣"],
    "悲傷": ["難過", "沮喪", "痛苦", "憂鬱", "失落", "悲", "傷心", "難受", "心痛"],
    "生氣": ["憤怒", "煩躁", "討厭", "厭惡", "憤慨", "生氣", "怒", "火大", "煩", "忿怒"],
    "焦慮": ["擔心", "緊張", "不安", "恐懼", "壓力", "焦慮", "怕", "擔憂", "空空"],
    "疲憊": ["累", "疲勞", "倦怠", "無力", "厭倦", "疲憊", "累死", "好累", "疲"],
    "震驚": ["驚", "震驚", "嚇", "意外", "驚訝", "驚喜"],
    "懼怕": ["怕", "恐懼", "害怕", "恐慌", "畏懼", "膽小"],
    "疑惑": ["疑惑", "疑問", "不懂", "困惑", "迷茫", "不解"]
}

def extract_emotion_tags(content: str) -> (List[str], str):
    words = jieba.lcut(content.lower())
    tags = []
    # 詞庫匹配
    for emotion, keywords in EMOTION_WORDS.items():
        if any(kw in words for kw in keywords):
            tags.append(emotion)
    
    # 使用transformers情感分析
    transformer_label = ""
    try:
        sentiment_pipeline = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment", device=0)  # GPU
        result = sentiment_pipeline(content)[0]
        label = result['label']  # 1 star to 5 stars
        confidence = result['score']
        if label in ['1 star', '2 stars']:
            if "悲傷" not in tags:
                tags.append("悲傷")
            transformer_label = "negative"
        elif label in ['4 stars', '5 stars']:
            if "快樂" not in tags:
                tags.append("快樂")
            transformer_label = "positive"
        elif label == '3 stars':
            transformer_label = "neutral"
    except:
        pass
    
    return list(set(tags)), transformer_label  # 去重

# 載入/儲存資料（極簡版，只記錄文字 + 時間）
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        records = json.load(f)
else:
    records = []  # [ {"time": "...", "content": "...", "tags": []}, ... ]

def save_records():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

# ------------------ 機器人本體 ------------------
intents = discord.Intents.default()
intents.message_content = True  # 如果之後想讀取一般訊息的話

class EchoClosetBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # 這裡可以放全域或特定伺服器同步指令
        # 因為主要是 DM 用，全域同步即可（但第一次要等一段時間）
        await self.tree.sync()  # ← 這行很重要！指令才會出現

bot = EchoClosetBot(intents=intents)


@bot.event
async def on_ready():
    print(f"殘響櫃已甦醒... 以 {bot.user} 的身份潛伏中")


# 核心指令：隨便丟一句話進櫃子
@bot.tree.command(name="echo", description="把一句話/情緒/碎片丟進櫃子裡，它會默默收下")
@app_commands.describe(content="想說什麼都可以，很醜也沒關係")
async def echo(interaction: discord.Interaction, content: str):
    current_time = datetime.datetime.now().time()
    ghost_start = datetime.time(2, 30)
    ghost_end = datetime.time(5, 0)
    is_ghost_time = ghost_start <= current_time <= ghost_end
    
    if ghost_mode and not is_ghost_time:
        await interaction.response.send_message("……現在不是說話的時候。夢裡見。", ephemeral=True)
        return
    
    now = datetime.datetime.now().isoformat(timespec='seconds')
    
    tags, transformer_label = extract_emotion_tags(content)
    
    entry = {
        "type": "echo",
        "time": now,
        "content": content.strip(),
        "tags": tags,
        "transformer_sentiment": transformer_label
    }
    
    records.append(entry)
    save_records()
    
    # 故意不回很多話，保持冷淡
    await interaction.response.send_message(
        "……收下了。", 
        ephemeral=True  # 只給你自己看
    )


# 查看最近 n 筆（最簡單的回顧）
@bot.tree.command(name="recent", description="讓櫃子吐出最近幾筆紀錄")
@app_commands.describe(count="想看幾筆？預設5", days="只看最近幾天內？可選")
async def recent(interaction: discord.Interaction, count: int = 5, days: Optional[int] = None):
    if not records:
        await interaction.response.send_message("櫃子是空的。", ephemeral=True)
        return

    filtered = records
    if days is not None:
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        filtered = [r for r in records if r["time"] >= cutoff]

    shown = filtered[-count:] if len(filtered) >= count else filtered
    
    if not shown:
        await interaction.response.send_message("這段時間什麼也沒有。", ephemeral=True)
        return

    msg = "最近的殘響：\n"
    for r in shown:
        msg += f"{r['time']} → {r['content']}\n"
    
    await interaction.response.send_message(msg, ephemeral=True)


# 分析最近一個月的常見情緒詞
@bot.tree.command(name="analyze", description="讓櫃子分析最近一個月最常出現的情緒詞")
async def analyze(interaction: discord.Interaction):
    if not records:
        await interaction.response.send_message("櫃子是空的，沒有什麼可分析的。", ephemeral=True)
        return

    # 最近一個月
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    recent_records = [r for r in records if r["time"] >= cutoff]

    if not recent_records:
        await interaction.response.send_message("最近一個月什麼也沒有。", ephemeral=True)
        return

    # 統計標籤
    tag_counts = {}
    for r in recent_records:
        for tag in r.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if not tag_counts:
        await interaction.response.send_message("最近一個月沒有檢測到明顯情緒詞。", ephemeral=True)
        return

    # 排序並顯示
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    msg = "最近一個月最常出現的情緒：\n"
    for tag, count in sorted_tags[:5]:  # 顯示前5
        msg += f"{tag}: {count} 次\n"

    await interaction.response.send_message(msg, ephemeral=True)


# 囤物清單（病態需求）
@bot.tree.command(name="hoard", description="把想買/想囤的東西丟進清單，設定冷靜期")
@app_commands.describe(description="東西的描述", cooldown_days="冷靜期天數，預設7天")
async def hoard(interaction: discord.Interaction, description: str, cooldown_days: int = 7):
    now = datetime.datetime.now().isoformat(timespec='seconds')
    
    entry = {
        "type": "hoard",
        "time": now,
        "description": description.strip(),
        "cooldown_days": cooldown_days,
        "status": "pending",
        "user_id": interaction.user.id
    }
    
    records.append(entry)
    save_records()
    
    await interaction.response.send_message(
        f"……收下了。{cooldown_days}天後再看看你還想不想買。", 
        ephemeral=True
    )


# 查看囤物清單
@bot.tree.command(name="hoard_list", description="看看你囤了什麼東西還沒處理")
async def hoard_list(interaction: discord.Interaction):
    user_hoards = [r for r in records if r.get("type") == "hoard" and r.get("user_id") == interaction.user.id and r.get("status") == "pending"]
    
    if not user_hoards:
        await interaction.response.send_message("清單是空的。", ephemeral=True)
        return
    
    msg = "你的囤物清單：\n"
    for r in user_hoards:
        expire_time = datetime.datetime.fromisoformat(r["time"]) + datetime.timedelta(days=r["cooldown_days"])
        msg += f"{r['time']} → {r['description']} (冷靜期至 {expire_time.strftime('%Y-%m-%d')})\n"
    
    await interaction.response.send_message(msg, ephemeral=True)


# 切換鬼魂模式
@bot.tree.command(name="toggle_ghost", description="切換鬼魂模式：只在凌晨2:30-5:00回應，其他時間飄忽")
async def toggle_ghost(interaction: discord.Interaction):
    global ghost_mode
    ghost_mode = not ghost_mode
    status = "啟用" if ghost_mode else "停用"
    await interaction.response.send_message(
        f"鬼魂模式已{status}。現在只在凌晨2:30-5:00正常回應，其他時間……會飄忽一點。", 
        ephemeral=True
    )


# 背景任務：檢查過期的囤物並嘲諷
@bot.event
async def on_ready():
    print(f"殘響櫃已甦醒... 以 {bot.user} 的身份潛伏中")
    bot.loop.create_task(check_expired_hoards())


async def check_expired_hoards():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.datetime.now()
        for r in records:
            if r.get("type") == "hoard" and r.get("status") == "pending":
                expire_time = datetime.datetime.fromisoformat(r["time"]) + datetime.timedelta(days=r["cooldown_days"])
                if now >= expire_time:
                    user = bot.get_user(r["user_id"])
                    if user:
                        try:
                            await user.send(f"喂，{r['description']} 已經過了冷靜期。你還想買嗎？還是說這又是你一時衝動？")
                            r["status"] = "expired"
                            save_records()
                        except:
                            pass  # 無法發送DM
        await asyncio.sleep(3600)  # 每小時檢查一次


# 毀滅鈕（真的很極端的那種）
@bot.tree.command(name="obliterate", description="把所有紀錄燒掉，30秒內不後悔就真的沒了")
async def obliterate(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**警告**：這會把所有紀錄永久刪除，沒有備份。\n"
        "如果你真的要，請在30秒內再打一次 `/obliterate_confirm`",
        ephemeral=True
    )


@bot.tree.command(name="obliterate_confirm", description="真的要燒掉全部紀錄（不可逆）")
async def obliterate_confirm(interaction: discord.Interaction):
    global records
    old_count = len(records)
    records = []
    save_records()
    
    await interaction.response.send_message(
        f"…燒掉了。{old_count} 條殘響，全部化為灰。", 
        ephemeral=True
    )


if __name__ == "__main__":
    bot.run(TOKEN)