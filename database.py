import sqlite3

DB_NAME = "tenders.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS tracked_tenders (
                       id TEXT PRIMARY KEY,          -- Номер закупки (Уникальный ключ))
                       customer TEXT,                -- Имя Государственного Заказчика
                       price TEXT,                   -- Сумма лота
                       statues TEXT DEFAULT 'NEW'    -- Статус обработки для чекера картелей ('NEW', 'ANALYZED')
                   )
    ''')
    conn.commit()
    conn.close()
    print("локальная база данных sqlite успешно инициализирована")

def add_tender(tender_id, customer, price):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO tracked_tenders(id, customer, price) VALUES(?, ?, ?)",
            (tender_id, customer, price)
        )

        conn.commit()
        return True
    
    except sqlite3.IntegrityError:
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()