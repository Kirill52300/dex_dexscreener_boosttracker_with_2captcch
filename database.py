import sqlite3
import hashlib
from datetime import datetime

class TokenDatabase:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_tokens (
                id TEXT PRIMARY KEY,
                pair_address TEXT UNIQUE NOT NULL,
                token_name TEXT,
                base_symbol TEXT,
                boosts INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_unique_id(self, pair_address):
        """Генерация уникального ID на основе pair_address"""
        return hashlib.md5(pair_address.encode()).hexdigest()
    
    def is_token_sent(self, pair_address, hours_delay=24):
        """Проверка, был ли токен уже отправлен с учетом временной задержки"""
        if not pair_address:
            return True  # Если нет адреса, считаем что уже отправлен
            
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Проверяем, есть ли токен в базе с учетом временной задержки
        cursor.execute('''
            SELECT COUNT(*) FROM sent_tokens 
            WHERE pair_address = ? 
            AND datetime(sent_at) > datetime('now', '-{} hours')
        '''.format(hours_delay), (pair_address,))
        
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def add_sent_token(self, pair_address, token_name, base_symbol, boosts, hours_delay=24):
        """Добавление токена в базу отправленных с учетом временной задержки"""
        if not pair_address:
            return False
            
        # Проверяем с учетом временной задержки
        if self.is_token_sent(pair_address, hours_delay):
            return False
        
        unique_id = self.generate_unique_id(pair_address)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # Удаляем старые записи этого токена (если есть)
            cursor.execute('DELETE FROM sent_tokens WHERE pair_address = ?', (pair_address,))
            
            # Добавляем новую запись
            cursor.execute('''
                INSERT INTO sent_tokens (id, pair_address, token_name, base_symbol, boosts)
                VALUES (?, ?, ?, ?, ?)
            ''', (unique_id, pair_address, token_name, base_symbol, boosts))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_sent_tokens_count(self):
        """Получение количества отправленных токенов"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM sent_tokens')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count

    def get_token_boosts(self, pair_address):
        """Получить текущее значение boosts для токена"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT boosts FROM sent_tokens WHERE pair_address = ?', (pair_address,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def update_token_boosts(self, pair_address, new_boosts):
        """Обновить значение boosts для токена"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('UPDATE sent_tokens SET boosts = ?, sent_at = CURRENT_TIMESTAMP WHERE pair_address = ?', (new_boosts, pair_address))
        conn.commit()
        conn.close()
