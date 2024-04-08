from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key= 'Chto ugodno'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

manager = LoginManager(app)

from db import *

db.init_app(app)

from posts import app as posts_bp


app.register_blueprint(posts_bp)


@manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def index():
    username = session.get('login')

    # Если имя пользователя есть в сессии, отобразите приветствие
    if username:
        greeting = f'Здравствуйте, {username}!'
    else:
        greeting = 'Здравствуйте!'

    return render_template('index.html', greeting=greeting)


@app.route('/myposts')
def myposts():
    if current_user.is_authenticated:
        user_articles = Article.query.filter_by(user_id=current_user.id).order_by(Article.date.desc()).all()
        access_articles = Article.query.join(DraftAccess, Article.id == DraftAccess.draft_id) \
            .filter(DraftAccess.user_id == current_user.id).all()

        user_articles_set = set(user_articles)
        access_articles_set = set(access_articles)

        # Объединяем результаты обоих запросов
        articles_set = user_articles_set.union(access_articles_set)

        # Сортируем статьи по дате
        articles = sorted(list(articles_set), key=lambda x: x.date, reverse=True)
        return render_template("my_posts.html", articles=articles)
    else:
        return redirect(url_for('login_page'))


@app.route('/create-article', methods=['POST', 'GET'])
@login_required
def create_article():
    if request.method == "POST":
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']
        status = request.form['status']  # Получаем значение статуса из формы

        # Установите `user_id` для нового поста, чтобы указать автора
        article = Article(title=title, intro=intro, text=text, user_id=current_user.id, status=status)

        try:
            db.session.add(article)
            # Получите логины пользователей, которым нужно предоставить доступ

            access_users = current_user.login+','+request.form.get('access_users')
            if access_users:
                access_user_logins = [login.strip() for login in access_users.split(',')]

                for login in access_user_logins:
                    user = User.query.filter_by(login=login).first()
                    if user:
                        draft_access = DraftAccess(draft_id=article.id, user_id=user.id)
                        db.session.add(draft_access)

            db.session.commit()
            return redirect('/posts')
        except:
            return "При добавлении статьи произошла ошибка"
    else:
        return render_template("create_article.html")


@app.route('/login', methods =['GET','POST'])
def login_page():
    login = request.form.get('login')
    password = request.form.get('password')

    if login and password:
        user = User.query.filter_by(login=login).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['login'] = user.login  # Установите имя пользователя в сессии
            next_page = request.args.get('next')

            return redirect(next_page or url_for('index'))
        else:
            flash('Введите логин и пароль заново')
    else:
        flash('Неверный логин или пароль')

    return render_template('login.html')


@app.route('/register', methods =['GET','POST'])
def register():
    login = request.form.get('login')
    password = request.form.get('password')
    password2 = request.form.get('password2')

    if request.method == 'POST':
        if not (login or password or password2):
            flash('Заполните все поля')
        elif password != password2:
            flash('Пароли не одинаковые')
        else:
            hash_pwd = generate_password_hash(password)
            new_user = User(login=login, password=hash_pwd)
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login_page'))

    return render_template('register.html')


@app.route('/logout', methods =['GET','POST'])
@login_required
def logout():
    logout_user()
    session.pop('login', None)  # Удалите имя пользователя из сессии
    return redirect(url_for('index'))


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('login_page') + '?next=' + request.url)

    return response


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)