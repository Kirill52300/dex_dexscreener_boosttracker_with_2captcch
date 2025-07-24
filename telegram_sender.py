import requests
import json
from datetime import datetime

class TelegramSender:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, text, parse_mode="HTML"):
        """Отправка сообщения в Telegram"""
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Response text: {response.text}")
            print(f"Ошибка отправки в Telegram: {e}")
            return False
    
    def escape_html(self, text):
        """Экранирование HTML символов"""
        if not text or text == "N/A" or text == "-":
            return text
        
        # Конвертируем в строку если это не строка
        text = str(text)
        
        # Экранируем HTML символы
        html_escape_table = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
            "/": "&#x2F;"
        }
        
        for char, escape in html_escape_table.items():
            text = text.replace(char, escape)
        
        return text
    
    def format_token_message(self, token_data):
        """Форматирование сообщения о токене"""
        # Получаем данные и экранируем их
        boosts = token_data.get("boosts", 0)
        position = self.escape_html(token_data.get("position", "N/A"))
        base_symbol = self.escape_html(token_data.get("base_symbol", "N/A"))
        quote_symbol = self.escape_html(token_data.get("quote_symbol", "N/A"))
        token_name = self.escape_html(token_data.get("token_name", "N/A"))
        price = self.escape_html(token_data.get("price", "N/A"))
        volume = self.escape_html(token_data.get("volume", "N/A"))
        liquidity = self.escape_html(token_data.get("liquidity", "N/A"))
        market_cap = self.escape_html(token_data.get("market_cap", "N/A"))
        dex = self.escape_html(token_data.get("dex", "N/A"))
        pair_age = self.escape_html(token_data.get("pair_age", "N/A"))
        
        pair_address = self.escape_html(token_data.get("pair_address", "N/A"))
        url = 'https://solscan.io/token/'+token_data.get("pair_address", "N/A")
        
        # Изменения цены - тоже экранируем
        price_5m = self.escape_html(token_data.get("price_change_5m", "-"))
        price_1h = self.escape_html(token_data.get("price_change_1h", "-"))
        price_6h = self.escape_html(token_data.get("price_change_6h", "-"))
        price_24h = self.escape_html(token_data.get("price_change_24h", "-"))
        
        # Формируем безопасное сообщение
        message = f"""🚀 <b>HIGH BOOST ALERT!</b> 🚀

⚡ <b>Boosts:</b> {boosts}
📊 <b>Position:</b> #{position}
🏷️ <b>Token:</b> {base_symbol}/{quote_symbol}
📝 <b>Name:</b> {token_name}
🏦 <b>DEX:</b> {dex}
⏰ <b>Age:</b> {pair_age}

💰 <b>Price:</b> {price}
📈 <b>Volume:</b> {volume}
💧 <b>Liquidity:</b> {liquidity}
🧢 <b>Market Cap:</b> {market_cap}

📊 <b>Price Changes:</b>
• 5m: {price_5m}
• 1h: {price_1h}
• 6h: {price_6h}
• 24h: {price_24h}

🔗 <b>Pair Address:</b> <code>{pair_address}</code>"""
        
        # Добавляем ссылку только если она есть
        if url:
            message += f"\n\n🔗 <a href=\"{url}\">View on Solscan</a>"
        
        message += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return message
