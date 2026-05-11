import sqlite3
from datetime import datetime

def get_db():
    conn = sqlite3.connect('hotels.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица отелей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            price_per_night INTEGER NOT NULL,
            rooms_total INTEGER NOT NULL,
            description TEXT
        )
    ''')
    
    # Таблица бронирований
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER NOT NULL,
            guest_name TEXT NOT NULL,
            guest_email TEXT NOT NULL,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            total_price INTEGER NOT NULL,
            FOREIGN KEY (hotel_id) REFERENCES hotels (id)
        )
    ''')
    
    # Добавим тестовые данные
    cursor.execute("SELECT COUNT(*) FROM hotels")
    if cursor.fetchone()[0] == 0:
        hotels = [
            ("Grand Hotel Moscow", "Москва", 5000, 10, "Роскошный отель в центре Москвы"),
            ("SPB Sea View", "Санкт-Петербург", 3500, 15, "Вид на Неву, уютные номера"),
            ("Sochi Sun Resort", "Сочи", 4200, 20, "Бассейн, рядом с морем"),
            ("Kazan Palace", "Казань", 3800, 8, "Традиционная татарская кухня"),
            ("Ekaterinburg City", "Екатеринбург", 2800, 12, "Бизнес-отель в центре"),
        ]
        for hotel in hotels:
            cursor.execute('''
                INSERT INTO hotels (name, city, price_per_night, rooms_total, description) 
                VALUES (?, ?, ?, ?, ?)
            ''', hotel)
    
    conn.commit()
    conn.close()

# Функции для работы с БД
def search_hotels(city, check_in, check_out):
    conn = get_db()
    cursor = conn.cursor()
    
    # Получаем все отели в городе
    cursor.execute("SELECT * FROM hotels WHERE city LIKE ?", (f'%{city}%',))
    hotels = cursor.fetchall()
    
    # Проверяем доступность на даты
    available = []
    for hotel in hotels:
        cursor.execute('''
            SELECT SUM(?) - COUNT(*) as available_rooms
            FROM bookings 
            WHERE hotel_id = ? 
            AND NOT (check_out <= ? OR check_in >= ?)
        ''', (hotel['rooms_total'], hotel['id'], check_in, check_out))
        
        result = cursor.fetchone()
        available_rooms = result[0] if result and result[0] else hotel['rooms_total']
        
        if available_rooms > 0:
            available.append(dict(hotel, available_rooms=available_rooms))
    
    conn.close()
    return available

def create_booking(hotel_id, guest_name, guest_email, check_in, check_out, total_price):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings (hotel_id, guest_name, guest_email, check_in, check_out, total_price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (hotel_id, guest_name, guest_email, check_in, check_out, total_price))
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id

def get_hotel(hotel_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hotels WHERE id = ?", (hotel_id,))
    hotel = cursor.fetchone()
    conn.close()
    return hotel

if __name__ == '__main__':
    init_db()
    print("База данных создана и заполнена тестовыми отелями!")