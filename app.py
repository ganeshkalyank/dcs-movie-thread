from flask import Flask,render_template,request,flash,url_for,redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin,LoginManager,login_required,login_user,logout_user,current_user
from os import environ
from werkzeug.security import generate_password_hash,check_password_hash

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("DATABASE_URL").replace("postgres","postgresql")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = environ.get("SECRET_KEY")

db = SQLAlchemy(app)

@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)

class Users(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(10))

class Movies(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    description = db.Column(db.String(10000))
    reviews = db.relationship("Reviews")

class Reviews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(10000))
    user = db.relationship("Users")
    user_id = db.Column(db.Integer,db.ForeignKey("users.id"))
    movie_id = db.Column(db.Integer,db.ForeignKey("movies.id"))

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "error"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route("/")
@login_required
def index():
    return render_template("index.html",movies=Movies.query.order_by(Movies.id).all())

@app.route("/login",methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = Users.query.filter_by(username=username).first()
        if not user:
            flash("User does not exist!",category="error")
        elif not check_password_hash(user.password,password=password):
            flash("Password is wrong!",category="error")
        else:
            login_user(user=user,remember=True)
            flash("Logged in successfully!",category="success")
            next = request.args.get("next")
            if next:
                url = next
            else:
                url = url_for("index")
            return redirect(url)
    return render_template("login.html")

@app.route("/signup",methods=["GET","POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        user = Users.query.filter_by(username=username).first()
        if user:
            flash("User already exists!",category="error")
        elif len(username)<3:
            flash("Username is too short!",category="error")
        elif len(password1)<8:
            flash("Password is too short!",category="error")
        elif password1!=password2:
            flash("Passwords does not match!",category="error")
        else:
            new_user = Users(username=username,password=generate_password_hash(password1),role="user")
            db.session.add(new_user)
            db.session.commit()
            flash("Account created succesfully!",category="success")
    return render_template("signup.html")

@app.route("/add_movie",methods=["GET","POST"])
@login_required
def add_movie():
    if current_user.role != "admin":
        flash("No access to this page for non-admin users!",category="error")
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        movie = Movies(name=name,description=description)
        db.session.add(movie)
        db.session.commit()
        flash("Movie added successfully!",category="success")
        return redirect(url_for("index"))
    return render_template("add_movie.html")

@app.route("/edit_movie/<int:id>",methods=["GET","POST"])
@login_required
def edit_movie(id):
    if current_user.role != "admin":
        flash("No access to this page for non-admin users!",category="error")
        return redirect(url_for("index"))
    current_movie = Movies.query.get_or_404(id)
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        movie = Movies.query.get(id)
        movie.name = name
        movie.description = description
        db.session.commit()
        flash("Movie edited successfully!",category="success")
        return redirect(url_for("index"))
    return render_template("edit_movie.html",movie=current_movie)

@app.route("/reviews/<int:id>",methods=["GET","POST"])
@login_required
def reviews(id):
    if request.method == "POST":
        content = request.form.get("content")
        review = Reviews(content=content,movie_id=id,user_id=current_user.id)
        db.session.add(review)
        db.session.commit()
        flash("Review posted successfully!",category="success")
    movie = Movies.query.get(id)
    reviews = movie.reviews
    return render_template("reviews.html",movie=movie,reviews=reviews)

@app.route("/delete_review/<int:id>")
@login_required
def delete_review(id):
    review_to_delete = Reviews.query.get(id)
    movie_id = review_to_delete.movie_id
    if current_user.id == review_to_delete.user_id:
        db.session.delete(review_to_delete)
        db.session.commit()
        flash("Review deleted succesfully!",category="success")
    return redirect(url_for("reviews",id=movie_id))

@app.route("/edit_review/<int:id>",methods=["GET","POST"])
@login_required
def edit_review(id):
    review_to_edit = Reviews.query.get(id)
    if request.method == "POST":
        content = request.form.get("content")
        if current_user.id == review_to_edit.user_id:
            review_to_edit.content = content
            db.session.commit()
            flash("Review updated successfully!",category="success")
        return redirect(url_for("reviews",id=review_to_edit.movie_id))
    return render_template("edit_review.html",review=review_to_edit)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run()