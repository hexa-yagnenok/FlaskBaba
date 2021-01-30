from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from email_validator import validate_email
from functools import wraps

app=Flask(__name__)
app.secret_key = 'some_secret'
app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="hexablog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"
mysql=MySQL(app)
#Kullanıcı Giriş Verify
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("You must be log in to see this page",category="danger")
            return redirect(url_for("login"))
    return decorated_function

# Kullanıcı Kayıt Formu
class Register(Form): 
    name = StringField(u"Your name :",validators=[validators.DataRequired(message="İsim belirleyiniz.")])
    email = StringField(u"Your E-mail :",validators=[validators.Email("Lütfen geçerli bir e-mail adresi giriniz.")])
    username = StringField(u"Your username :",validators=[validators.DataRequired(message="Kullanıcı adı belirleyiniz.")])
    password = PasswordField(u"Your password :",validators=[
        validators.DataRequired(message=u"Şifre belirleyiniz."),
        validators.Length(8,16,u"Şifreniz en az 8, en fazla 16 karakterli olmalıdır."),
        validators.EqualTo(fieldname="confirmPassword",message=u"Parolanız uyuşmuyor")])
    confirmPassword = PasswordField(u"Confirm your password")
class Login(Form):
    email = StringField(u"Your E-mail :",validators=[validators.Email("Lütfen geçerli bir e-mail adresi giriniz.")])
    password = PasswordField(u"Your password :")
@app.route("/register",methods=["GET","POST"])
def register():
    form = Register(request.form)
    if request.method=="POST" and form.validate():
        name=form.name.data
        email=form.email.data
        username=form.username.data
        password=sha256_crypt.encrypt(form.password.data)
        cursor=mysql.connection.cursor()
        queue = 'INSERT INTO users (name,email,username,password) VALUES (%s,%s,%s,%s)'
        cursor.execute(queue,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Succesfully registered",category="success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)
#login
@app.route("/login",methods = ["GET","POST"])
def login():
    form = Login(request.form)
    if request.method=="POST" and form.validate():
        email=form.email.data
        password=form.password.data
        cursor=mysql.connection.cursor()
        queue=f"SELECT * FROM users WHERE email='{email}'"
        result=cursor.execute(queue)
        if result>0:
            data=cursor.fetchone()
            real_password=data["password"]
            if(sha256_crypt.verify(password,real_password)):
                flash("You're logged in succesfully",category="success")
                session["logged_in"] = True
                session["username"] = data["username"]
                return redirect(url_for("index"))
            else:
                flash("USER NOT FOUND",category="danger")
                return redirect(url_for("login"))
        else:
            flash("USER NOT FOUND",category="danger")
            return redirect(url_for("login"))
    else:
        return render_template("login.html",form=form)
#index
@app.route("/")
def index():
    return render_template("index.html")
#about
@app.route("/about")
def about():    
    return render_template("about.html")
#logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
#dashboad
@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()
    query="SELECT * from articles WHERE author=%s"
    result=cursor.execute(query,(session["username"],))
    if result>0:
        articles=cursor.fetchall()
        print(len(articles))
        return render_template("dashboard.html",articles=articles,number=len(articles))
    else:
        return render_template("dashboard.html")
#Makale Ekleme
@app.route("/addarticle",methods=["GET","POST"])
@login_required
def addarticle():
    form=ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title = form.title.data
        content=form.content.data
        
        cursor=mysql.connection.cursor()
        query=f"INSERT INTO articles (title,author,content) VALUES ('{title}','{session['username']}','{content}')"
        cursor.execute(query)
        mysql.connection.commit()
        cursor.close()
        flash("Shared","success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html",form=form)
# Makale Form
class ArticleForm(Form):
    title = StringField("Title",validators=[validators.Length(min=5,max=100)])
    content=TextAreaField("Content",validators=[validators.Length(min=10)])
#Makale sayfası
@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    query="SELECT * FROM articles ORDER by id desc"
    result=cursor.execute(query)
    if result>0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

#detay sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor=mysql.connection.cursor()
    query = f"SELECT * FROM articles WHERE id={id}"
    result=cursor.execute(query)
    if result>0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")
#makale update
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        query= f"SELECT * FROM articles WHERE id={id} and author='{session['username']}'"
        result=cursor.execute(query)
        if result==0:
            flash("You can't edit","danger")
            return redirect(url_for("index"))
        else:
            article=cursor.fetchone()
            form=ArticleForm()
            form.title.data=article['title']
            form.content.data=article['content']
            return render_template("update.html",form=form)
    else:
        # POST REQUEST
        form=ArticleForm(request.form)
        newTitle=form.title.data
        newContent=form.content.data
        cursor=mysql.connection.cursor()
        query=f"UPDATE articles SET title='{newTitle}',content='{newContent}' WHERE id={id}"
        cursor.execute(query)
        mysql.connection.commit()
        flash("Article succesfully updated","success")
        return redirect(url_for("dashboard"))


# makale sil
@app.route("/remove/<string:id>")
@login_required
def remove(id):
    cursor=mysql.connection.cursor()
    query = f"SELECT * FROM articles WHERE id={id}"
    result=cursor.execute(query)
    if result>0:
        data=cursor.fetchone()
        if(session["username"]==data["author"]):
            query=f"DELETE from articles WHERE id={id}"
            cursor.execute(query)
            mysql.connection.commit()
            flash(f"You removed {data['title']}","success")
            return redirect(url_for("dashboard"))
        else:
            flash("You can't remove","danger")
            return redirect(url_for("index"))
    else:
        flash("You can't remove","danger")
        return redirect(url_for("index"))
#arama url
@app.route("/search",methods=["GET","POST"])
def search():
    if (request.method=="GET"):
        return redirect(url_for("index"))
    else:
        keyword=request.form.get("keyword")
        cursor=mysql.connection.cursor()
        query=f"SELECT * FROM articles WHERE title like '%{keyword}%'"
        print(query)
        result=cursor.execute(query)
        if result==0:
            flash("Couldn't find article","warning")
            return redirect(url_for("articles"))
        else:
            articles=cursor.fetchall()
            return render_template("articles.html",articles=articles)


if __name__ == "__main__":
    app.run(debug=True)