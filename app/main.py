from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3
import os
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-12345'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем папку для загрузок если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Декоратор для проверки авторизации админа
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('У вас нет доступа к этой странице', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки авторизации пользователя
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Пожалуйста, войдите в аккаунт', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    conn = sqlite3.connect('hotels.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Удаляем старую базу если есть
    if os.path.exists('hotels.db'):
        os.remove('hotels.db')
        print("Старая база удалена")
    
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
            description TEXT,
            image_url TEXT,
            is_featured INTEGER DEFAULT 0,
            rating REAL DEFAULT 4.0
        )
    ''')
    
    # Таблица бронирований
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER NOT NULL,
            user_id INTEGER,
            guest_name TEXT NOT NULL,
            guest_email TEXT NOT NULL,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            total_price INTEGER NOT NULL,
            guests_count INTEGER DEFAULT 1,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hotel_id) REFERENCES hotels (id)
        )
    ''')
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Добавляем тестовых пользователей
    users = [
        ('admin', 'admin@hotelbooking.com', 'admin123', 1),
        ('user', 'user@example.com', 'user123', 0),
    ]
    cursor.executemany("INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)", users)
    
    # Добавляем отели
    hotels = [
        ('Лотте Отель', 'Москва', 7000, 30, 'Роскошный 5-звездочный отель в самом центре Москвы', '/static/uploads/20260511_233259_hotel2.jpg', 1, 5.0),
        ('История', 'Санкт-Петербург', 6000, 50, 'Уютный отель с панорамным видом на Неву', '/static/uploads/20260511_233400_hotel3.jpg', 1, 5.0),
        ('Отель ДЭМ', 'Сухум', 8000, 20, 'Курортный отель с собственным пляжем', '/static/uploads/20260511_233501_hotel4.jpg', 1, 5.0),
        ('Дворец Трезини', 'Санкт-Петербург', 10000, 21, 'Элегантный отель в историческом центре', '/static/uploads/20260511_233553_hotel5.jpg', 1, 5.0),
        ('Отель Долина 960', 'Эсто-Садок', 5000, 20, 'Современный отель в горах', '/static/uploads/20260511_233716_hotel6.jpg', 1, 4.0),
        ('Элементс', 'Киров', 4000, 40, 'Бизнес-отель в деловом центре', '/static/uploads/20260511_233825_hotel7.jpg', 1, 4.0),
    ]
    cursor.executemany('''INSERT INTO hotels (name, city, price_per_night, rooms_total, description, image_url, is_featured, rating) 
                        VALUES (?,?,?,?,?,?,?,?)''', hotels)
    
    conn.commit()
    conn.close()
    print("База данных создана с 6 отелями")

# ========== МАРШРУТЫ ==========

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hotels WHERE is_featured = 1 ORDER BY rating DESC LIMIT 6")
    featured_hotels = cursor.fetchall()
    cursor.execute("SELECT city, COUNT(*) as count FROM hotels GROUP BY city")
    cities = cursor.fetchall()
    conn.close()
    return render_template('index.html', featured_hotels=featured_hotels, cities=cities)

@app.route('/hotels')
def all_hotels():
    page = request.args.get('page', 1, type=int)
    per_page = 9
    search_query = request.args.get('search', '')
    city_filter = request.args.get('city', '')
    sort_by = request.args.get('sort', 'rating')
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM hotels WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND name LIKE ?"
        params.append(f'%{search_query}%')
    
    if city_filter:
        query += " AND city = ?"
        params.append(city_filter)
    
    if sort_by == 'price_asc':
        query += " ORDER BY price_per_night ASC"
    elif sort_by == 'price_desc':
        query += " ORDER BY price_per_night DESC"
    elif sort_by == 'rating':
        query += " ORDER BY rating DESC"
    elif sort_by == 'name':
        query += " ORDER BY name ASC"
    
    cursor.execute(f"SELECT COUNT(*) as count FROM ({query})", params)
    total = cursor.fetchone()['count']
    
    offset = (page - 1) * per_page
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    hotels = cursor.fetchall()
    
    cursor.execute("SELECT DISTINCT city FROM hotels ORDER BY city")
    cities = cursor.fetchall()
    
    conn.close()
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('all_hotels.html', 
                         hotels=hotels, 
                         cities=cities,
                         total=total,
                         page=page,
                         total_pages=total_pages,
                         search_query=search_query,
                         city_filter=city_filter,
                         sort_by=sort_by)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, 0)", 
                         (username, email, password))
            conn.commit()
            flash('Регистрация успешна! Теперь вы можете войти', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким именем или email уже существует', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            flash(f'Добро пожаловать, {username}!', 'success')
            
            if user['is_admin']:
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hotels ORDER BY id DESC")
    hotels = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()
    return render_template('admin.html', hotels=hotels, total_bookings=total_bookings, total_users=total_users)

@app.route('/admin/add_hotel', methods=['POST'])
@admin_required
def add_hotel():
    name = request.form.get('name')
    city = request.form.get('city')
    price = request.form.get('price')
    rooms = request.form.get('rooms')
    description = request.form.get('description')
    is_featured = 1 if request.form.get('is_featured') else 0
    rating = request.form.get('rating', 4.0)
    
    image_url = request.form.get('image_url', '')
    file = request.files.get('hotel_image')
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        image_url = f'/static/uploads/{filename}'
    elif not image_url:
        image_url = '/static/uploads/hotel1.jpg'
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO hotels (name, city, price_per_night, rooms_total, description, image_url, is_featured, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, city, price, rooms, description, image_url, is_featured, rating))
    conn.commit()
    conn.close()
    
    flash('Отель успешно добавлен!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/edit_hotel/<int:hotel_id>', methods=['GET', 'POST'])
@admin_required
def edit_hotel(hotel_id):
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        city = request.form.get('city')
        price = request.form.get('price')
        rooms = request.form.get('rooms')
        description = request.form.get('description')
        is_featured = 1 if request.form.get('is_featured') else 0
        rating = request.form.get('rating', 4.0)
        
        image_url = request.form.get('image_url', '')
        file = request.files.get('hotel_image')
        
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_url = f'/static/uploads/{filename}'
        elif not image_url:
            cursor.execute("SELECT image_url FROM hotels WHERE id = ?", (hotel_id,))
            old_hotel = cursor.fetchone()
            image_url = old_hotel['image_url'] if old_hotel else '/static/uploads/hotel1.jpg'
        
        cursor.execute('''
            UPDATE hotels 
            SET name = ?, city = ?, price_per_night = ?, rooms_total = ?, 
                description = ?, image_url = ?, is_featured = ?, rating = ?
            WHERE id = ?
        ''', (name, city, price, rooms, description, image_url, is_featured, rating, hotel_id))
        conn.commit()
        conn.close()
        
        flash('Отель успешно обновлен!', 'success')
        return redirect(url_for('admin'))
    
    cursor.execute("SELECT * FROM hotels WHERE id = ?", (hotel_id,))
    hotel = cursor.fetchone()
    conn.close()
    
    if not hotel:
        flash('Отель не найден', 'error')
        return redirect(url_for('admin'))
    
    return render_template('edit_hotel.html', hotel=hotel)

@app.route('/admin/delete_hotel/<int:hotel_id>')
@admin_required
def delete_hotel(hotel_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE hotel_id = ?", (hotel_id,))
    cursor.execute("DELETE FROM hotels WHERE id = ?", (hotel_id,))
    conn.commit()
    conn.close()
    
    flash('Отель и все его бронирования удалены', 'success')
    return redirect(url_for('admin'))

@app.route('/hotel/<int:hotel_id>')
def hotel_detail(hotel_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hotels WHERE id = ?", (hotel_id,))
    hotel = cursor.fetchone()
    conn.close()
    return render_template('hotel_detail.html', hotel=hotel)

@app.route('/search', methods=['POST'])
def search():
    city = request.form.get('city')
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hotels WHERE city LIKE ?", (f'%{city}%',))
    hotels = cursor.fetchall()
    conn.close()
    
    return render_template('hotels.html', hotels=hotels, check_in=check_in, check_out=check_out, city=city)

@app.route('/book/<int:hotel_id>')
@login_required
def book_form(hotel_id):
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hotels WHERE id = ?", (hotel_id,))
    hotel = cursor.fetchone()
    conn.close()
    
    if not hotel or not check_in or not check_out:
        flash('Ошибка: неверные данные', 'error')
        return redirect(url_for('index'))
    
    nights = (datetime.strptime(check_out, '%Y-%m-%d') - datetime.strptime(check_in, '%Y-%m-%d')).days
    total_price = hotel['price_per_night'] * nights
    
    return render_template('booking.html', 
                         hotel=hotel, 
                         check_in=check_in, 
                         check_out=check_out, 
                         nights=nights, 
                         total_price=total_price)

@app.route('/confirm', methods=['POST'])
@login_required
def confirm():
    hotel_id = request.form.get('hotel_id')
    guest_name = request.form.get('guest_name')
    guest_email = request.form.get('guest_email')
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    total_price = request.form.get('total_price')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings (hotel_id, user_id, guest_name, guest_email, check_in, check_out, total_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (hotel_id, session['user_id'], guest_name, guest_email, check_in, check_out, total_price))
    conn.commit()
    booking_id = cursor.lastrowid
    
    cursor.execute("SELECT name FROM hotels WHERE id = ?", (hotel_id,))
    hotel_name = cursor.fetchone()[0]
    conn.close()
    
    return render_template('success.html', 
                         booking_id=booking_id, 
                         guest_name=guest_name, 
                         hotel_name=hotel_name, 
                         check_in=check_in, 
                         check_out=check_out, 
                         total_price=total_price)

@app.route('/my_bookings')
@login_required
def my_bookings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, h.name as hotel_name, h.image_url
        FROM bookings b 
        JOIN hotels h ON b.hotel_id = h.id 
        WHERE b.user_id = ? 
        ORDER BY b.booking_date DESC
    ''', (session['user_id'],))
    bookings = cursor.fetchall()
    conn.close()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/support', methods=['GET', 'POST'])
def support():
    if request.method == 'POST':
        message = request.form.get('message')
        if not message:
            flash('Пожалуйста, введите сообщение', 'error')
            return redirect(url_for('support'))
        
        auto_reply = generate_auto_reply(message)
        flash('Сообщение отправлено!', 'success')
        return render_template('support.html', user_message=message, bot_reply=auto_reply, show_reply=True)
    
    return render_template('support.html', show_reply=False)

def generate_auto_reply(message):
    message_lower = message.lower()
    responses = {
        'бронировани': "📅 Чтобы забронировать отель: перейдите на главную, найдите отель, выберите даты и заполните форму.",
        'отмен': "❌ Для отмены бронирования напишите на support@hotelbooking.com",
        'цена': "💰 Цены от 4000 до 10000 ₽ за ночь.",
        'привет': "👋 Здравствуйте! Я виртуальный помощник. Чем могу помочь?",
    }
    for key, reply in responses.items():
        if key in message_lower:
            return reply
    return "🤖 Спасибо за обращение! Наш специалист свяжется с вами."

# Всегда создаём базу при запуске
init_db()

if __name__ == '__main__':
    app.run(debug=True)