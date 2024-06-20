from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired
from datetime import datetime
from threading import Thread, Event
from werkzeug.serving import make_server
from threading import Thread
import time
import sched
import shutil
import sqlite3
import os
from urllib.parse import quote


app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'SZ'
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Константы для папок загрузки
UPLOAD_FOLDER_AVATARS = 'static/avatars'

# Настройки для допустимых расширений файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Установка папки загрузки для аватаров
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER_AVATARS


conn = sqlite3.connect('mybase.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        avatar TEXT,
        is_admin INTEGER DEFAULT 0
    )
''')

conn.commit()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS albums (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        link TEXT NOT NULL,
        cover_image TEXT,
        slider_category TEXT NOT NULL DEFAULT 'default'
    )
''')


cursor.execute('''
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prew TEXT NOT NULL,
        link TEXT NOT NULL
    )
''')

conn.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT NOT NULL,
        mail TEXT NOT NULL,
        text TEXT NOT NULL
    )
''')

cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            user_id INTEGER,
            album_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (album_id) REFERENCES albums(id),
            PRIMARY KEY (user_id, album_id)
        )
    ''')

# Запрос для добавления администратора
admin_username = 'admin'
admin_password = '654321'
admin_email = 'admin@example.com'
hashed_password = generate_password_hash(admin_password)

# Проверка существования администратора
cursor.execute(
    'SELECT * FROM users WHERE username = ? AND is_admin = 1',
    (admin_username,)
)
admin_exists = cursor.fetchone()

# Вставка администратора, если его нет
if not admin_exists:
    cursor.execute(
        'INSERT INTO users (username, password, email, is_admin) VALUES (?, ?, ?, ?)',
        (admin_username, hashed_password, admin_email, 1)
    )
    conn.commit()
    print('Администратор успешно добавлен в базу данных.')
else:
    print('Администратор уже существует в базе данных.')

# Закрытие соединения с базой данных
conn.close()

def is_admin_by_username(username):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE username = ?', (username,))
    is_admin = cursor.fetchone()
    conn.close()
    print(f"Is admin for {username}: {is_admin}")  # Debug print
    return is_admin[0] == 1 if is_admin else False  # Изменяем возвращаемое значение на булево

class User(UserMixin):
    def __init__(self, user_id, username, avatar):
        self.id = user_id
        self.username = username
        self.avatar = avatar

def is_authenticated(self):
        return True  # Все пользователи аутентифицированы

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        user = User(user_data[0], user_data[1], user_data[4])
        user.is_admin = is_admin_by_username(user_data[1])  # Установка атрибута is_admin
        return user
    return None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_id_by_username(username):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None


@app.route('/register', methods=['GET', 'POST'])
def register():
    avatar = None
    if request.method == 'POST':
        print("POST request received for registration")
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        avatar = request.files['avatar'] if 'avatar' in request.files else None

        if not username or not password or not email:
            print("Invalid input: Please enter username, password, and email")
            return render_template('register.html', error='Пожалуйста, введите имя пользователя, пароль и email.', avatar=avatar)

        if len(password) < 6 or len(password) > 20:
            print("Invalid password length: Password should be between 6 and 20 characters")
            return render_template('register.html', error='Пароль должен быть от 6 до 20 символов.', avatar=avatar)

        if not avatar:
            print("Avatar not uploaded")
            # Return success message instead of error, as registration can proceed without avatar
            flash('Аватар не загружен. Регистрация будет завершена без аватара.')

        conn = sqlite3.connect('mybase.db')
        cursor = conn.cursor()

        # Check if the username already exists
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user:
            print("Username already exists")
            conn.close()
            return render_template('register.html', error='Пользователь с таким именем уже существует.', avatar=avatar)

        # Check if the email already exists
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user_by_email = cursor.fetchone()
        if user_by_email:
            print("Email already registered")
            conn.close()
            return render_template('register.html', error='Пользователь с таким email уже зарегистрирован.', avatar=avatar)

        # Save avatar if provided
        new_avatar_filename = save_avatar(avatar, username)
        if new_avatar_filename or not avatar:  # Proceed with registration even if avatar is not uploaded
            print("Registration successful")
            cursor.execute(
                'INSERT INTO users (username, password, email, avatar) VALUES (?, ?, ?, ?)',
                (username, generate_password_hash(password), email, new_avatar_filename)
            )
            conn.commit()
            conn.close()
            flash('Регистрация успешна. Теперь вы можете войти.')
            return redirect(url_for('login'))

    print("Rendering registration template")
    return render_template('register.html', avatar=avatar)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Пожалуйста, введите имя пользователя и пароль.')
            return render_template('login.html')

        conn = sqlite3.connect('mybase.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            user_obj = User(user[0], user[1], user[4])
            user_obj.is_admin = is_admin_by_username(username)  # Установка флага администратора
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверные имя пользователя или пароль.')

    return render_template('login.html')


def save_avatar(avatar, username):
    try:
        if avatar:
            if allowed_file(avatar.filename):
                filename = secure_filename(avatar.filename)
                # Добавляем идентификатор пользователя к имени файла
                user_id = get_user_id_by_username(username)
                new_filename = f"{user_id}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER_AVATARS'], new_filename)
                avatar.save(filepath)
                return new_filename  # Возвращаем новое имя файла
            else:
                print("Invalid file format for avatar")
                flash('Недопустимый формат файла для аватара. Пожалуйста, используйте форматы PNG, JPG, JPEG или GIF.')
        else:
            print("Avatar not uploaded")
            return None
    except Exception as e:
        print(f"Error saving avatar: {e}")
        flash('Ошибка при загрузке аватара. Пожалуйста, повторите попытку.')

    return None

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    # Проверяем, отправлен ли файл
    if 'avatar' not in request.files:
        flash('Файл не выбран')
        return redirect(request.url)

    avatar = request.files['avatar']

    # Проверяем, выбран ли файл
    if avatar.filename == '':
        flash('Файл не выбран')
        return redirect(request.url)

    # Проверяем допустимость типа файла
    if avatar and allowed_file(avatar.filename):
        filename = secure_filename(avatar.filename)
        user_id = current_user.id
        new_filename = f"{user_id}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        avatar.save(filepath)

        # Обновляем запись пользователя с ссылкой на аватар
        conn = sqlite3.connect('mybase.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET avatar = ? WHERE id = ?', (new_filename, user_id))
        conn.commit()
        conn.close()

        flash('Файл успешно загружен')
        return redirect(url_for('dashboard'))
    else:
        flash('Недопустимый тип файла')
        return redirect(request.url)

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM albums')
    albums = cursor.fetchall()

    cursor.execute('SELECT * FROM news')
    news = cursor.fetchall()

    cursor.execute('SELECT * FROM feedback')
    feedback = cursor.fetchall()

# Запрос альбомов из желаемого
    user_id = current_user.id
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT albums.id, albums.title, albums.artist, albums.link, albums.cover_image
        FROM wishlist
        JOIN albums ON wishlist.album_id = albums.id
        WHERE wishlist.user_id = ?
    ''', (user_id,))
    wishlist_albums = cursor.fetchall()
    conn.close()

    if current_user.is_authenticated:
        is_admin = "Да" if current_user.is_admin else "Нет"
        app.logger.info(f'User {current_user.username} is admin: {is_admin}')
        return render_template('dashboard.html', user=current_user, albums=albums, news=news, feedback=feedback, wishlist_albums=wishlist_albums)
    else:
        return redirect(url_for('login'))
    

@app.route('/add_to_wishlist/<int:album_id>', methods=['POST'])
@login_required
def add_to_wishlist(album_id):
    user_id = current_user.id
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    
    # Проверка, существует ли запись с такой комбинацией user_id и album_id
    cursor.execute('SELECT * FROM wishlist WHERE user_id = ? AND album_id = ?', (user_id, album_id))
    existing_entry = cursor.fetchone()
    
    if existing_entry:
        flash('Этот альбом уже добавлен в желаемое.')
    else:
        cursor.execute('INSERT INTO wishlist (user_id, album_id) VALUES (?, ?)', (user_id, album_id))
        conn.commit()
        flash('Альбом успешно добавлен в желаемое.')
    
    conn.close()
    return redirect(url_for('dashboard'))


@app.route('/remove_from_wishlist/<int:album_id>', methods=['POST'])
@login_required
def remove_from_wishlist(album_id):
    user_id = current_user.id
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    
    # Удаление записи с такой комбинацией user_id и album_id
    cursor.execute('DELETE FROM wishlist WHERE user_id = ? AND album_id = ?', (user_id, album_id))
    conn.commit()
    conn.close()
    
    flash('Альбом успешно убран из желаемого.')
    return redirect(url_for('dashboard'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли.')
    return redirect(url_for('index'))

@app.route('/aboutus')
def aboutus():
    return render_template('about us.html')

@app.route('/alternative')
def alternative():
    return render_template('alternative.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/hiphop')
def hiphop():
    return render_template('hip-hop.html')

@app.route('/pop')
def pop():
    return render_template('pop.html')

@app.route('/rap')
def rap():
    return render_template('rap.html')

@app.route('/rock')
def rock():
    return render_template('rock.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = FeedbackForm()
    if form.validate_on_submit():
        nickname = form.nickname.data
        mail = form.mail.data
        text = form.text.data
        add_feedback_to_database(nickname, mail, text)
        flash('Ваше сообщение успешно отправлено')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM albums')
    albums = cursor.fetchall()

    cursor.execute('SELECT * FROM news')
    news = cursor.fetchall()

    cursor.execute('SELECT * FROM feedback')
    feedback = cursor.fetchall()

    conn.close()

    return render_template('index.html', albums=albums, news=news, form=form, feedback=feedback)


@app.route('/album/<int:album_id>')
def album(album_id):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM albums WHERE id = ?', (album_id,))
    album_data = cursor.fetchone()

    if album_data:
        album = {
            'id': album_data[0],
            'title': album_data[1],
            'artist': album_data[2],
            'link': album_data[3],
            'cover_image': f"{album_data[4]}", # Обновляем путь к файлу обложки альбома
            'slider_category': album_data[5] 
        }

        conn.close()
        return redirect(url_for('index'))
    

class AlbumForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    artist = StringField('Artist', validators=[DataRequired()])
    link = StringField('Link', validators=[DataRequired()])
    cover_image = FileField('Cover Image', validators=[FileAllowed(['jpg', 'png'])])
    slider_category = SelectField('Категория', choices=[('default', 'Популярное'), ('other0', 'Рекомендуемое'), ('other1', 'Поп'), ('other2', 'Хип-хоп'), ('other3', 'Рэп'), ('other4', 'Рок'), ('other5', 'Альтернатива')])
    submit = SubmitField('Опубликовать')

def add_album_to_database(title, artist, link, cover_image_filename, slider_category):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO albums (title, artist, link, cover_image, slider_category) VALUES (?, ?, ?, ?, ?)', (title, artist, link, cover_image_filename, slider_category))
    conn.commit()
    conn.close()   

@app.route('/add_album', methods=['GET', 'POST'])
@login_required
def add_album():
    form = AlbumForm()
    if form.validate_on_submit():
        # Получение данных из формы
        title = form.title.data
        artist = form.artist.data
        link = form.link.data
        cover_image = form.cover_image.data
        slider_category = form.slider_category.data

        # Сохранение обложки альбома
        if cover_image and allowed_file(cover_image.filename):
            filename = secure_filename(cover_image.filename)
            cover_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            cover_image.save(cover_image_path)
        else:
            flash('Ошибка при загрузке файла обложки альбома.')
            return redirect(url_for('add_album'))

        # Добавление альбома в базу данных
        add_album_to_database(title, artist, link, filename, slider_category)

        flash('Альбом успешно добавлен')
        return redirect(url_for('index'))

    # Получаем альбомы из базы данных
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM albums')
    albums = cursor.fetchall()
    conn.close()

    return render_template('add_album.html', form=form, albums=albums)


# Форма редактирования альбома
class EditAlbumForm(FlaskForm):
    title = StringField('Новый заголовок', validators=[DataRequired()])
    artist = StringField('Новый исполнитель', validators=[DataRequired()])
    link = StringField('Новая ссылка', validators=[DataRequired()])
    slider_category = SelectField('Новая категория', choices=[('default', 'Популярное'), ('other0', 'Рекомендуемое'), ('other1', 'Поп'), ('other2', 'Хип-хоп'), ('other3', 'Рэп'), ('other4', 'Рок'), ('other5', 'Альтернатива')])
    submit = SubmitField('Обновить')

@app.route('/edit_album/<int:album_id>', methods=['GET', 'POST'])
@login_required
def edit_album(album_id):
    if not current_user.is_admin:
        flash('Доступ к админ-панели разрешен только администраторам.')
        return redirect(url_for('index'))

    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM albums WHERE id = ?', (album_id,))
    album = cursor.fetchone()
    conn.close()

    if request.method == 'POST':
        new_title = request.form.get('title', '')
        new_artist = request.form.get('artist', '')
        new_link = request.form.get('link', '')
        new_image = request.files.get('image')
        new_slider_category = request.form.get('slider_category', 'default')

        if new_title and new_artist:
            conn = sqlite3.connect('mybase.db')
            cursor = conn.cursor()

            if new_image and allowed_file(new_image.filename):
                filename = secure_filename(new_image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                new_image.save(image_path)
                cursor.execute('UPDATE albums SET title = ?, artist = ?, link = ?, cover_image = ?, slider_category = ? WHERE id = ?', 
                               (new_title, new_artist, new_link, filename, new_slider_category, album_id))
            else:
                cursor.execute('UPDATE albums SET title = ?, artist = ?, link = ?, slider_category = ? WHERE id = ?', 
                               (new_title, new_artist, new_link, new_slider_category, album_id))

            conn.commit()
            conn.close()
            flash('Альбом успешно отредактирован.')
            return redirect(url_for('dashboard'))
        else:
            flash('Ошибка: Не удалось обновить альбом. Укажите название и исполнителя.')

    return render_template('edit_album.html', album=album)



@app.route('/delete_album/<int:album_id>', methods=['POST'])
@login_required
def delete_album(album_id):
    if current_user.is_admin:
        conn = sqlite3.connect('mybase.db')
        cursor = conn.cursor()
        # Удаление альбома из базы данных
        cursor.execute('DELETE FROM albums WHERE id = ?', (album_id,))
        conn.commit()
        conn.close()
        flash('Альбом успешно удален')
    else:
        flash('У вас нет прав на удаление альбомов.')
    return redirect(url_for('dashboard'))


@app.route('/new/<int:new_id>')
def new(new_id):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM news WHERE id = ?', (new_id,))
    new_data = cursor.fetchone()

    if new_data:
        new = {
            'id': new_data[0],
            'prew': new_data[1],
            'link': new_data[2],
        }
       
        conn.close()
        return redirect(url_for('index'))
    

def add_new_to_database(prew, link):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO news (prew, link) VALUES (?, ?)', (prew, link))
    conn.commit() 
    conn.close()



class NewForm(FlaskForm):
    prew = StringField('Prew', validators=[DataRequired()])
    link = StringField('Link', validators=[DataRequired()])
    submit = SubmitField('Опубликовать')


@app.route('/add_new', methods=['GET', 'POST'])
@login_required
def add_new():
    form = NewForm()
    if form.validate_on_submit():
        # Получение данных из формы
        prew = form.prew.data
        link = form.link.data
        add_new_to_database(prew, link)

        flash('Новость успешно добавлена')
        return redirect(url_for('index'))

    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM news')
    news = cursor.fetchall()
    conn.close()

    return render_template('add_new.html', form=form, news=news)

@app.route('/delete_new/<int:new_id>', methods=['POST'])
@login_required
def delete_new(new_id):
    if current_user.is_admin:
        conn = sqlite3.connect('mybase.db')
        cursor = conn.cursor()
        # Удаление альбома из базы данных
        cursor.execute('DELETE FROM news WHERE id = ?', (new_id,))
        conn.commit()
        conn.close()
        flash('Новость успешно удален')
    else:
        flash('У вас нет прав на удаление новостей.')
    return redirect(url_for('dashboard'))


@app.route('/feedback/<int:feedback_id>')
def feedback(feedback_id):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM feedback WHERE id = ?', (feedback_id,))
    feedback_data = cursor.fetchone()

    if feedback_data:
        feedback = {
            'id': feedback_data[0],
            'nickname': feedback_data[1],
            'mail': feedback_data[2],
            'text': feedback_data[3]
        }
       
        conn.close()
        return redirect(url_for('index'))    

def add_feedback_to_database(nickname, mail, text):
    conn = sqlite3.connect('mybase.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO feedback (nickname, mail, text) VALUES (?, ?, ?)', (nickname, mail, text))
    conn.commit() 
    conn.close()    


class FeedbackForm(FlaskForm):
    nickname = StringField('Имя', validators=[DataRequired()])
    mail = StringField('Почта', validators=[DataRequired()])
    text = TextAreaField('Сообщение', validators=[DataRequired()])
    submit = SubmitField('Отправить')

@app.route('/delete_feedback/<int:feedback_id>', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    if current_user.is_admin:
        conn = sqlite3.connect('mybase.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
        conn.commit()
        conn.close()
        flash('Отзыв успешно удален')
    else:
        flash('У вас нет прав на удаление отзывов.')
    
    # После удаления редиректим на dashboard, а не на feedback
    return redirect(url_for('dashboard'))








scheduler = sched.scheduler(time.time, time.sleep)

def start_server(stop_event):
    app.run(debug=True, use_reloader=False)

def backup_database(source_path, backup_dir, stop_event):
    while not stop_event.is_set():
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        shutil.copy(source_path, backup_path)
        print(f"Резервная копия создана: {backup_filename}")
        time.sleep(21600)  # Повторяем каждые 6 часов

def start_scheduler(stop_event):
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(0, 1, backup_database, (source_path, backup_dir, stop_event))
    scheduler.run()

if __name__ == '__main__':
   
    source_path = os.path.join(app.root_path, 'mybase.db')
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    stop_event = Event()

    scheduler_thread = Thread(target=start_scheduler, args=(stop_event,), daemon=True)
    scheduler_thread.start()

    try:
        app.run(debug=True, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("Stopping server and scheduler...")
        stop_event.set()
        scheduler_thread.join()