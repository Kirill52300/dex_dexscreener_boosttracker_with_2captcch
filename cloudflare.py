import os
import re
import json
from playwright.sync_api import sync_playwright
from twocaptcha import TwoCaptcha
from fake_useragent import UserAgent

ua = UserAgent()
CAPTCHA_TOKEN = None

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json not found")
        return {}
    except json.JSONDecodeError:
        print("Error reading config.json")
        return {}

# Initialize solver with API key from config
config = load_config()
TWO_CAPTCHA_KEY = config.get('two_captcha_key', '')
solver = TwoCaptcha(TWO_CAPTCHA_KEY)

def handle_console(msg):
    """Обработчик консольных сообщений для извлечения параметров капчи"""
    if '{"type":"TurnstileTaskProxyless"' in msg.text:
        params = json.loads(msg.text)
        print("Получены параметры капчи:", params)
        
        try:
            result = solver.turnstile(
                url=params['websiteURL'],
                sitekey=params['websiteKey'],
                data=params.get('data'),
                pagedata=params.get('pagedata'),
                action=params.get('action', 'interactive'),
                useragent=params['userAgent']
            )
            global CAPTCHA_TOKEN
            CAPTCHA_TOKEN = result.get('code')
            print("Получен токен капчи:", CAPTCHA_TOKEN)
        except Exception as e:
            print("Ошибка решения капчи:", e)

def captcha_solver():
    with sync_playwright() as p:
        # Загрузка сохраненного состояния, если существует
       
        storage_path = "browser_state.json"
        chrome_ug = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
      
        
        context = p.chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            headless=False,
            user_agent=chrome_ug
        )
        
        with open('user_agent.txt', 'w') as f:
            f.write(chrome_ug)
        context.clear_cookies()
        
        if os.path.exists(storage_path):
            context.add_cookies(json.load(open(storage_path))['cookies'])
            
        page = context.new_page()
        
        # Подписка на консольные сообщения
        page.on('console', handle_console)
        
        # Инъекция скрипта для перехвата параметров капчи
        page.add_init_script("""
            const checkTurnstile = setInterval(() => {
                if (window.turnstile) {
                    clearInterval(checkTurnstile);
                    window.turnstile.render = (a, b) => {
                        const params = {
                            type: "TurnstileTaskProxyless",
                            websiteKey: b.sitekey,
                            websiteURL: window.location.href,
                            data: b.cData,
                            pagedata: b.chlPageData,
                            action: b.action,
                            userAgent: navigator.userAgent
                        };
                        console.log(JSON.stringify(params));
                        window.tsCallback = b.callback;
                        return 'foo';
                    };
                }
            }, 50);
        """)
        
       # page.goto('https://2captcha.com/')
        page.goto("https://dexscreener.com/solana?rankBy=trendingScoreH24&order=desc&dexIds=pumpswap,raydium,pumpfun&ads=1&boosted=1&profile=1")
        
        # Ждем загрузки страницы
        page.wait_for_timeout(5000)
        
        # Проверяем, есть ли challenge
        max_retries = 8
        retry = 0
        captcha_needed = False
        
        while max_retries > retry:
            page_content = page.content().lower()
            
            if "just a moment" in page_content or "checking your browser" in page_content:
             #
             # print(f"Cloudflare challenge detected, attempt {retry + 1}")
                captcha_needed = True
                
                if CAPTCHA_TOKEN is None:
                    page.wait_for_timeout(2000)
                    retry += 1
                else:
                    break
            else:
                context.storage_state(path=storage_path)
                with open("cookies.json", "w") as f:
                       f.write(json.dumps(context.cookies()))
                print("No Cloudflare challenge detected")
                return True
        
        # Отправка токена через callback если есть
        if CAPTCHA_TOKEN and captcha_needed:
            try:
                page.evaluate(f"tsCallback('{CAPTCHA_TOKEN}')")
                print("Токен отправлен в callback")
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Ошибка при отправке токена (возможно капча не нужна): {e}")
        
        page.screenshot(path='./new.png')
        
        # Сохраняем состояние браузера
        #context.storage_state(path=storage_path)
        
        # Получаем куки
        cookies = context.cookies()
        page.wait_for_timeout(5000)
        print(f"Cookies получены: {len(cookies)}")
        
        # Завершение работы
        context.storage_state(path=storage_path)
        with open("cookies.json", "w") as f:
                       f.write(json.dumps(context.cookies()))
        context.close()
        
        # Сброс токена
       
        
        return cookies

