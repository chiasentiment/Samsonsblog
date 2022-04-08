from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, ForeignKey
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##CONFIGURE TABLES
Base = declarative_base()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    usercomments = relationship("Comments", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")

    usercomments = relationship("Comments", back_populates="blogs")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class Comments(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="usercomments")

    # blog linking
    # Create a Foreign Key, blog_posts.id. The  blog_posts refers to table name of the blog table
    blog_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Create a reference to the Blog object, the blogs refer to the blogs property in the Blogpost class
    blogs = relationship("BlogPost", back_populates="usercomments")

    body = db.Column(db.Text, nullable=False)


db.create_all()

admin = False


def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        print(admin)
        if not admin:
            return abort(403, description="unauthorized")
        return function(*args, **kwargs)

    return wrapper_function


@app.route('/')
def get_all_posts():
    if current_user.is_authenticated:
        posts = BlogPost.query.all()
        return render_template("index.html", all_posts=posts, authenticated=current_user.is_authenticated, admin=admin)
    else:
        return redirect(url_for('login', authenticated=current_user.is_authenticated))


@app.route('/register', methods=['GET', 'POST'])
def register():
    global admin
    form = RegisterForm()
    if form.validate_on_submit():
        user_record = User.query.filter_by(email=form.email.data).first()
        if not user_record:
            new_user = User(
                email=form.email.data,
                password=generate_password_hash(form.password.data),
                name=form.name.data,
            )
            db.session.add(new_user)
            db.session.commit()
            user_record = User.query.filter_by(email=form.email.data).first()

            login_user(user_record)
            if current_user.id == 1:
                admin = True
            else:
                admin = False
            return redirect(url_for('get_all_posts', authenticated=current_user.is_authenticated, admin=admin))
        else:
            flash("User Already registered. Please Login")
            return redirect(url_for('login'))
    return render_template("register.html", form=form, authenticated=current_user.is_authenticated)


@app.route('/login', methods=['GET', 'POST'])
def login():
    global admin
    form = LoginForm()
    if form.validate_on_submit():
        user_record = User.query.filter_by(email=form.email.data).first()
        if not user_record:
            flash("User Email Not Found. Please Register")
        else:
            if check_password_hash(user_record.password, form.password.data):
                login_user(user_record)
                if current_user.id == 1:
                    admin = True
                else:
                    admin = False
                return redirect(url_for('get_all_posts', authenticated=current_user.is_authenticated, admin=admin))
            else:
                flash("Incorrect Password. Please Try again.")
    return render_template("login.html", form=form, authenticated=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login', authenticated=current_user.is_authenticated))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
@login_required
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        new_comment = Comments(
            body=form.body.data,
            author=current_user,
            blogs=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    blog_comments = Comments.query.filter_by(blog_id=post_id).all()
    # for blog_record in blog_records:
    #     print (blog_record.body)
    return render_template("post.html", form=form, post=requested_post, comments=blog_comments, authenticated=current_user.is_authenticated,admin=admin, user_name=current_user.name)


@app.route("/about")
def about():
    return render_template("about.html", authenticated=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", authenticated=current_user.is_authenticated)


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    print(current_user.id)
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts", authenticated=current_user.is_authenticated, admin=admin))
    return render_template("make-post.html", form=form, authenticated=current_user.is_authenticated, admin=admin)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id, authenticated=current_user.is_authenticated, admin=admin))
    return render_template("make-post.html", form=edit_form, authenticated=current_user.is_authenticated, admin=admin,
                           is_edit=True)


@app.route("/delete/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts', authenticated=current_user.is_authenticated, admin=admin))


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
