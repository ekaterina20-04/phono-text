from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from db import *
import git
from datetime import datetime
import os

app = Blueprint('posts', __name__, url_prefix='/posts')


def check_directory(directory):
    path_to_dir=f'{os.path.dirname(os.path.abspath(__file__))}/{directory}'
    if not(os.path.isdir(path_to_dir)):
        os.makedirs(path_to_dir, exist_ok=True)
    try:
        repo = git.Repo(path_to_dir)
    except:
        repo = git.Repo.init(path_to_dir)


@app.route('/')
def posts():
    articles = Article.query.filter_by(status='published').order_by(Article.date.desc()).all()
    authors={}
    for article in articles:
        authors[article.id]=User.query.get(article.user_id)
    return render_template("posts.html", articles=articles, authors=authors)


@app.route('/<int:id>', methods=['GET'])
@login_required
def posts_detail(id):
    article = Article.query.filter_by(id=id).first()
    author = User.query.get(article.user_id)
    draft_access = DraftAccess.query.filter_by(draft_id=id)
    access_id=[draft.user_id for draft in draft_access]
    if article and current_user.id in access_id:
        return render_template("posts_detail.html", article=article, author=author, flag=True)
    elif article:
        return render_template("posts_detail.html", article=article, author=author, flag=False)
    else:
        return "Статья не найдена или не опубликована"




@app.route('/<int:id>/del', methods=['GET'])
@login_required
def posts_delete(id):
    article = Article.query.get(id)

    if article and article.user_id == current_user.id:
        try:
            db.session.delete(article)
            db.session.commit()
            return redirect('/posts')
        except:
            return "При удалении статьи произошла ошибка"
    else:
        return "Вы не можете удалить этот пост"


@app.route('/<int:id>/update', methods=['POST', 'GET'])
@login_required
def post_update(id):
    try:
        article = Article.query.get(id)
        draft_access = DraftAccess.query.filter_by(draft_id=id, user_id=current_user.id).first()
        if article:
            if draft_access or current_user.id == article.user_id:
                if request.method == "POST":
                    article.title = request.form['title'].strip()
                    article.intro = request.form['intro'].strip()
                    article.text = request.form['text'].strip()
                    check_directory("articles")
                    git_check = save_changes(request.form['text'].strip(),fr"\articles\article_{id}",request.form['commit']) #Какие-то табы были, поэтому strip()
                    if git_check:
                        print("Успешное сохранение!")
                        print(get_file_history(fr"articles/article_{id}"))
                    else:
                        print("Что то не так!")
                    db.session.add(article)
                    # Получите логины пользователей, которым нужно предоставить доступ
                    access_users = current_user.login + ',' + request.form.get('access_users')
                    if access_users and article.user_id == current_user.id:
                        access_user_logins = [login.strip() for login in access_users.split(',')]

                        for login in access_user_logins:
                            user = User.query.filter_by(login=login).first()
                            if user:
                                draft_access = DraftAccess(draft_id=article.id, user_id=user.id)
                                db.session.add(draft_access)
                    try:
                        db.session.commit()
                        if request.form.get("update"):
                            return redirect('/posts')
                        elif request.form.get("save_changes"):
                            return redirect(f'/posts/{article.id}/update')

                    except:
                        return "При редактировании статьи произошла ошибка"


                else:
                    return render_template("post_update.html", article=article)
            else:
                return "Вы не имеете доступа к редактированию этого черновика"
        else:
            return "Статья не найдена"
    except Exception as e:
        print(e)


@app.route('/<int:id>/publish-draft', methods=['GET'])
@login_required
def publish_draft(id):
    article = Article.query.get(id)
    if article is None:
        return "Черновик не найден"

    if article.user_id != current_user.id:
        return "Вы не можете опубликовать чужой черновик"

    # Создайте новую статью на основе черновика и установите статус "опубликовано"
    article.status="published"


    try:
        db.session.commit()

        return redirect('/posts')
    except:
        return "При публикации статьи произошла ошибка"

@app.route('/<int:id>/get_file_history', methods=['GET'])
@login_required
def get_file_history(id):
    return render_template("get_file_history.html", history=get_git_history(fr"\articles\article_{id}"))




def save_changes(edit_text,file_path,cmt):
    check_directory("articles")
    try:
        with open(os.path.dirname(os.path.abspath(__file__))+file_path,'w',encoding='utf-8') as f:
            f.write(edit_text)
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        repo=git.Repo('articles')
        repo.index.add([os.path.dirname(os.path.abspath(__file__))+file_path])
        repo.index.commit(f"Commit: {cmt} Date: {formatted_datetime} Edited file: {file_path}")
        print(f"Commit: {cmt} Date: {formatted_datetime} Edited file: {file_path}")
        repo.index.update()
        return True
    except Exception as e:
        print(e)
        return False

def get_git_history(file_path):
    check_directory("articles")
    commits = list(git.Repo('articles').iter_commits())
    all_commits = dict()
    for commit in commits:
        msg = commit.message
        print(msg)
        if msg[msg.find('Edited file: ') + 13:] == file_path:
            files = commit.tree.traverse()
            for file in files:
                if file.path == file_path[file_path.rfind('\\') + 1:]:
                    file_content = file.data_stream.read().decode('utf-8')  # Чтение содержимого файла
                    date = msg[msg.find('Date: ')+6:msg.find('Edited file: ')]
                    cmt=msg[8:msg.find('Date: ')]
                    all_commits[date] = {"file_content":file_content,"commit":cmt}
    return all_commits