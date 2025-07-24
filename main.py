from  cloudflare import captcha_solver
import os
import requests
import json
from bs4 import BeautifulSoup
import re
from database import TokenDatabase
from telegram_sender import TelegramSender
from fake_useragent import UserAgent
user_agent = None
ug = UserAgent()
if os.path.exists('user_agent.txt'):
 with open('user_agent.txt', 'r') as f:
    user_agent = f.read().strip()
else:
 user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome'
SESSION = None
HEADERS = None
# Загрузка конфигурации
def load_config():
    """Загрузка конфигурации из config.json"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Файл config.json не найден. Создайте его с настройками.")
        return None
    except json.JSONDecodeError:
        print("Ошибка чтения config.json. Проверьте синтаксис.")
        return None

def process_high_boost_tokens(tokens, config, db, telegram):
    """Обработка токенов с высоким количеством бустов и отслеживание изменений"""
    if not config:
        return

    boost_threshold = config.get("boost_threshold", 500)
    hours_delay = config.get("hours_delay", 24)
    sent_count = 0
    boost_change_sent_count = 0

    print(f"Проверяем токены с количеством бустов > {boost_threshold} (задержка: {hours_delay}ч)")
    TEMP_PAIR = []
    for token in tokens:
        boosts = token.get("boosts", 0)
        pair_address = token.get("pair_address", "")

        if pair_address:
            real_pair_address = None
            print(pair_address)
            try:
                resp_base_adress = SESSION.get('https://dexscreener.com/solana/' + pair_address, headers=HEADERS, timeout=5)
                soup_resp = BeautifulSoup(resp_base_adress.text, 'html.parser')
                spans = soup_resp.find_all('span', class_='chakra-text custom-72rvq0')
                span = spans[1] if len(spans) > 1 else None
                real_pair_address = span['title'] if span and span.has_attr('title') else pair_address
            except Exception as e:
                print(e)
            if not real_pair_address in TEMP_PAIR:
                TEMP_PAIR.append(real_pair_address)
            else:
                continue
            token["pair_address"] = real_pair_address
            
            # Получаем предыдущее значение boosts из базы
            prev_boosts = db.get_token_boosts(real_pair_address)

            # Проверка на изменение boosts >= 5
            if prev_boosts is not None and boosts - prev_boosts >= 5:
                # Форматируем и отправляем сообщение о смене boosts
                message = telegram.format_token_message(token)
                message = f"⚡ <b>BOOSTS CHANGED!</b> ({prev_boosts} → {boosts})\n\n" + message
                if telegram.send_message(message):
                    db.update_token_boosts(real_pair_address, boosts)
                    boost_change_sent_count += 1
                    print(f"✅ Изменение бустов отправлено для {token.get('base_symbol')} ({prev_boosts} → {boosts})")
                else:
                    print(f"❌ Ошибка отправки изменения бустов: {token.get('base_symbol')}")
                continue  # Не отправлять обычное сообщение, если уже отправили по изменению

            if boosts > boost_threshold:
                # Проверяем, не отправляли ли уже этот токен с учетом временной задержки
                if not db.is_token_sent(real_pair_address, hours_delay):
                    # Форматируем и отправляем сообщение
                    message = telegram.format_token_message(token)
                    if telegram.send_message(message):
                        # Добавляем в базу данных с учетом временной задержки
                        success = db.add_sent_token(
                            real_pair_address,
                            token.get("token_name", ""),
                            token.get("base_symbol", ""),
                            boosts,
                            hours_delay
                        )
                        if success:
                            sent_count += 1
                            print(f"✅ Отправлен токен {token.get('base_symbol')} с {boosts} бустами")
                        else:
                            print(f"⚠️ Ошибка добавления в БД: {token.get('base_symbol')}")
                    else:
                        print(f"❌ Ошибка отправки: {token.get('base_symbol')}")
                else:
                    print(f"⏭️ Пропущен (отправлен менее {hours_delay}ч назад): {token.get('base_symbol')}")

    total_sent = db.get_sent_tokens_count()
    print(f"Отправлено новых токенов: {sent_count}")
    print(f"Отправлено сообщений об изменении бустов: {boost_change_sent_count}")
    print(f"Всего записей в БД: {total_sent}")

def fetch_dexscreener_data():
    """Fetch boosted tokens data from DexScreener"""
    url = "https://dexscreener.com/solana?rankBy=activeBoosts&order=desc&dexIds=pumpswap,raydium,pumpfun&boosted=1&profile=1"
    
    # Try to get cookies from cloudflare bypass first
    cookies = None
    
  #  print(user_agent)
    
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
       
        "user-agent": user_agent,
    }
    global HEADERS
    HEADERS = headers
    
    # Convert cookies to requests format if available
    session = requests.Session()
    if os.path.exists("cookies.json"):
        with open("cookies.json", "r") as f:
         cookies = json.load(f)
    if cookies:
        cookie_dict = {}
        for cookie in cookies:
           # print(cookie)
            cookie_dict[cookie['name']] = cookie['value']
        session.cookies.update(cookie_dict)
     #   print(f"Using cookies: {list(cookie_dict.keys())}")
    global SESSION
    SESSION = session
    try:
        response = session.get(url, headers=headers)
    #    print(f"Response status: {response.status_code}")
    #    print(response.text[:500])  # Print first 500 characters of response for debugging
        
        # Check if we got Cloudflare challenge page
        if "just a moment" in response.text.lower() or "checking your browser" in response.text.lower() or "cf-challenge-running" in response.text.lower():
        #    print("Cloudflare challenge detected in HTTP response")
            try:
           #     print("Attempting Cloudflare bypass...")
                cookies = captcha_solver()
                if cookies:
                    print(f"Retrieved {len(cookies)} cookies successfully")
                    # Retry request with new cookies
                    cookie_dict = {}
                    for cookie in cookies:
                        cookie_dict[cookie['name']] = cookie['value']
                    session.cookies.update(cookie_dict)
                    response = session.get(url, headers=headers)
                  #  print(f"Retry response status: {response.status_code}")
                else:
                    print("No cookies retrieved from browser")
            except Exception as e:
                print(f"Cloudflare bypass failed: {e}")
         
        response.raise_for_status()
        
        # Save response for debugging
        with open("example.html", "w", encoding='utf-8') as f:
            f.write(response.text)
            
        # Parse HTML and extract data
        table_data = parse_dexscreener_html(response.text)
        
        # Convert to JSON and print
        json_data = json.dumps(table_data, indent=2, ensure_ascii=False)
      #  print("DexScreener Boosted Tokens Data:")
      # # print(json_data)
        
        # Загружаем конфигурацию и инициализируем компоненты
        config = load_config()
        if config:
            # Инициализация базы данных
            db_filename = config.get("database", {}).get("filename", "sent_tokens.db")
            db = TokenDatabase(db_filename)
            
            # Инициализация Telegram отправителя
            telegram_config = config.get("telegram", {})
            bot_token = telegram_config.get("bot_token")
            chat_id = telegram_config.get("chat_id")
            
            if bot_token and chat_id:
                telegram = TelegramSender(bot_token, chat_id)
                
                # Обработка токенов с высоким количеством бустов
                tokens = table_data.get("tokens", [])
                process_high_boost_tokens(tokens, config, db, telegram)
            else:
                print("⚠️ Telegram настройки не найдены в config.json")
        
        return table_data
        
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def parse_dexscreener_html(html_content):
    """Parse HTML content to extract table data"""
    soup = BeautifulSoup(html_content, 'html.parser')
    print("Starting HTML parsing...")
    
    # First, try to extract from JavaScript variables
    script_tags = soup.find_all('script')
    server_data = None
    
    print(f"Found {len(script_tags)} script tags")
    
    # Look for various patterns of data in scripts
    for i, script in enumerate(script_tags):
        if script.string:
            script_content = script.string
            
            # Check for different data patterns
            patterns_to_check = [
                ('__SERVER_DATA', r'window\.__SERVER_DATA\s*=\s*({.*?});'),
                ('__INITIAL_STATE__', r'window\.__INITIAL_STATE__\s*=\s*({.*?});'),
                ('__DATA__', r'window\.__DATA__\s*=\s*({.*?});'),
                ('pageProps', r'"pageProps"\s*:\s*({.*?"pairs".*?})'),
                ('pairs', r'"pairs"\s*:\s*(\[.*?\])')
            ]
            
            for pattern_name, pattern in patterns_to_check:
                try:
                    match = re.search(pattern, script_content, re.DOTALL)
                    if match:
                        json_data = match.group(1)
                        server_data = json.loads(json_data)
                        print(f"Found data using pattern '{pattern_name}' in script {i}")
                        break
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            if server_data:
                break
    
    # If no server data found, try to parse visible HTML elements
    if not server_data:
        print("No server data found, parsing visible HTML...")
        return parse_visible_table(soup)
    
    # Extract relevant data from server data
    table_data = {
        "timestamp": server_data.get("time"),
        "source": "server_data",
        "tokens": extract_token_data(server_data)
    }
    
    return table_data

def parse_visible_table(soup):
    """Parse visible table if server data is not available"""
    print("Parsing visible table elements...")
    
    table_data = {
        "tokens": [],
        "headers": [],
        "source": "html_parsing"
    }
    
    # Ищем основную таблицу DexScreener
    table = soup.select_one('.ds-dex-table.ds-dex-table-top')
    if not table:
        print("DexScreener table not found")
        return table_data
    
    print("Found DexScreener table")
    
    # Извлекаем заголовки
    headers_row = table.select_one('.ds-dex-table-th')
    if headers_row:
        headers = []
        header_elements = headers_row.select('.ds-table-th')
        for header in header_elements:
            button = header.select_one('.ds-table-th-button')
            if button:
                headers.append(button.get_text(strip=True))
        table_data["headers"] = headers
        print(f"Found headers: {headers}")
    
    # Извлекаем строки токенов
    token_rows = table.select('.ds-dex-table-row.ds-dex-table-row-top')
    print(f"Found {len(token_rows)} token rows")
    
    for row in token_rows:
        token_data = {}
        
        # Извлекаем номер позиции
        position_elem = row.select_one('.ds-dex-table-row-badge-pair-no')
        if position_elem:
            position_text = position_elem.get_text(strip=True)
            # Убираем символ # если есть
            position = position_text.replace('#', '').strip()
            token_data["position"] = position
        
        # Извлекаем иконку DEX
        dex_icon = row.select_one('.ds-dex-table-row-dex-icon')
        if dex_icon:
            token_data["dex"] = dex_icon.get('title', '')
        
        # Извлекаем токен информацию
        token_cell = row.select_one('.ds-dex-table-row-col-token')
        if token_cell:
            # Символ базового токена
            base_symbol = token_cell.select_one('.ds-dex-table-row-base-token-symbol')
            if base_symbol:
                token_data["base_symbol"] = base_symbol.get_text(strip=True)
            
            # Символ котируемого токена
            quote_symbol = token_cell.select_one('.ds-dex-table-row-quote-token-symbol')
            if quote_symbol:
                token_data["quote_symbol"] = quote_symbol.get_text(strip=True)
            
            # Название токена
            token_name_elem = token_cell.select_one('.ds-dex-table-row-base-token-name-text')
            if token_name_elem:
                token_data["token_name"] = token_name_elem.get_text(strip=True)
            
            # ВАЖНО: Количество бустов
            boosts_elem = token_cell.select_one('.ds-dex-table-row-base-token-name-boosts')
            if boosts_elem:
                boosts_text = boosts_elem.get_text(strip=True)
                # Извлекаем только число из текста
                import re
                boosts_match = re.search(r'(\d+)', boosts_text)
                if boosts_match:
                    token_data["boosts"] = int(boosts_match.group(1))
                else:
                    token_data["boosts"] = 0
            
            # Бейдж (CLMM, CPMM и т.д.)
            badge = token_cell.select_one('.ds-dex-table-row-badge-label')
            if badge:
                token_data["badge"] = badge.get_text(strip=True)
        
        # Извлекаем цену
        price_cell = row.select_one('.ds-dex-table-row-col-price')
        if price_cell:
            token_data["price"] = price_cell.get_text(strip=True)
        
        # Извлекаем возраст пары
        age_cell = row.select_one('.ds-dex-table-row-col-pair-age')
        if age_cell:
            token_data["pair_age"] = age_cell.get_text(strip=True)
        
        # Извлекаем транзакции
        txns_cell = row.select_one('.ds-dex-table-row-col-txns')
        if txns_cell:
            token_data["transactions"] = txns_cell.get_text(strip=True)
        
        # Извлекаем объем
        volume_cell = row.select_one('.ds-dex-table-row-col-volume')
        if volume_cell:
            token_data["volume"] = volume_cell.get_text(strip=True)
        
        # Извлекаем мейкеров
        makers_cell = row.select_one('.ds-dex-table-row-col-makers')
        if makers_cell:
            token_data["makers"] = makers_cell.get_text(strip=True)
        
        # Извлекаем изменения цены
        price_changes = {
            "5m": row.select_one('.ds-dex-table-row-col-price-change-m5'),
            "1h": row.select_one('.ds-dex-table-row-col-price-change-h1'),
            "6h": row.select_one('.ds-dex-table-row-col-price-change-h6'),
            "24h": row.select_one('.ds-dex-table-row-col-price-change-h24')
        }
        
        for period, cell in price_changes.items():
            if cell:
                change_elem = cell.select_one('.ds-change-perc')
                if change_elem:
                    # Проверяем, есть ли данные или пустое значение
                    empty_val = change_elem.select_one('.ds-table-empty-val')
                    if empty_val:
                        token_data[f"price_change_{period}"] = "-"
                    else:
                        token_data[f"price_change_{period}"] = change_elem.get_text(strip=True)
        
        # Извлекаем ликвидность
        liquidity_cell = row.select_one('.ds-dex-table-row-col-liquidity')
        if liquidity_cell:
            token_data["liquidity"] = liquidity_cell.get_text(strip=True)
        
        # Извлекаем рыночную капитализацию
        mcap_cell = row.select_one('.ds-dex-table-row-col-market-cap')
        if mcap_cell:
            token_data["market_cap"] = mcap_cell.get_text(strip=True)
        
        # Извлекаем ссылку
        href = row.get('href')
      
        
       
     
        if href:
            token_data["url"] = f"https://dexscreener.com{href}"
            # Извлекаем адрес пары из URL
            token_data["pair_address"] = href.split('/')[-1] if href else ""
        else:
            # Если нет href, создаем уникальный ID на основе символа и названия
            base_symbol = token_data.get("base_symbol", "")
            token_name = token_data.get("token_name", "")
            if base_symbol and token_name:
                # Создаем псевдо-адрес для уникальности
                pseudo_address = f"{base_symbol}_{token_name}_{position}".lower().replace(" ", "_")
                token_data["pair_address"] = pseudo_address
        
        # Добавляем токен только если есть основные данные
        if (token_data.get("base_symbol") and 
            token_data.get("token_name") and 
            token_data.get("pair_address")):
            table_data["tokens"].append(token_data)
    
  #  print(f"Extracted {len(table_data['tokens'])} tokens from HTML")
    
    # Сортируем по количеству бустов (по убыванию)
    table_data["tokens"].sort(key=lambda x: x.get("boosts", 0), reverse=True)
    
    return table_data

def extract_token_data(server_data):
    """Extract token information from server data"""
    tokens = []
    
    # Look for token data in various possible locations
    possible_keys = ['pairs', 'tokens', 'data', 'results', 'items', 'list']
    
    def search_nested(obj, keys_to_find):
        """Recursively search for keys in nested object"""
        found_data = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in keys_to_find and isinstance(value, list):
                    found_data.extend(value)
                elif isinstance(value, (dict, list)):
                    found_data.extend(search_nested(value, keys_to_find))
        elif isinstance(obj, list):
            for item in obj:
                found_data.extend(search_nested(item, keys_to_find))
        
        return found_data
    
    # Search for data
    found_items = search_nested(server_data, possible_keys)
    
    for item in found_items:
        if isinstance(item, dict):
            # Extract token info with fallbacks
            base_token = item.get("baseToken", {})
            quote_token = item.get("quoteToken", {})
            
            token_info = {
                "pair_address": item.get("pairAddress", item.get("address", "")),
                "base_token": {
                    "address": base_token.get("address", ""),
                    "symbol": base_token.get("symbol", ""),
                    "name": base_token.get("name", "")
                },
                "quote_token": {
                    "symbol": quote_token.get("symbol", ""),
                    "name": quote_token.get("name", "")
                },
                "price_usd": item.get("priceUsd", ""),
                "volume_24h": item.get("volume", {}).get("h24", ""),
                "liquidity_usd": item.get("liquidity", {}).get("usd", ""),
                "price_change_24h": item.get("priceChange", {}).get("h24", ""),
                "market_cap": item.get("marketCap", ""),
                "dex_id": item.get("dexId", ""),
                "chain_id": item.get("chainId", ""),
                "boosted": item.get("boosted", False),
                "boost_percent": item.get("boostPercent", 0)
            }
            tokens.append(token_info)
    
   # print(f"Extracted {len(tokens)} tokens from server data")
    return tokens

if __name__ == "__main__":
    # Fetch and display DexScreener data
    fetch_dexscreener_data()