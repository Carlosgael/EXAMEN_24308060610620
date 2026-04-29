from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt

app = Flask(__name__)
app.secret_key = "clave_super_segura"

client = MongoClient("mongodb://localhost:27017/")
db = client["gestor_tareas"]

users_col = db["users"]
tasks_col = db["tasks"]

def current_user():
    return session.get("user_email")


@app.route("/")
def index():
    if current_user():
        return redirect(url_for("tasks_page"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = users_col.find_one({"email": email})

        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            session["user_email"] = email
            flash("Has iniciado sesión.", "success")
            return redirect(url_for("tasks_page"))

        flash("Email o contraseña incorrectos.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Completa todos los campos.", "warning")

        elif password != confirm:
            flash("Las contraseñas no coinciden.", "danger")

        elif users_col.find_one({"email": email}):
            flash("Ya existe una cuenta con ese email.", "warning")

        else:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

            users_col.insert_one({
                "name": name,
                "email": email,
                "password": hashed
            })

            flash("Registro exitoso.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        user = users_col.find_one({"email": email})

        if user:
            new_pass = bcrypt.hashpw("123456".encode("utf-8"), bcrypt.gensalt())

            users_col.update_one(
                {"email": email},
                {"$set": {"password": new_pass}}
            )

            flash("Nueva contraseña: 123456", "info")
            return redirect(url_for("login"))

        flash("Email no encontrado.", "danger")

    return render_template("reset_password.html")


@app.route("/tasks")
def tasks_page():
    if not current_user():
        return redirect(url_for("login"))

    email = current_user()

    user = users_col.find_one({"email": email})
    user_tasks = list(tasks_col.find({"email": email}))

    return render_template("tasks.html", user=user, tasks=user_tasks)


@app.route("/tasks/add", methods=["POST"])
def add_task():
    if not current_user():
        return redirect(url_for("login"))

    email = current_user()

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title:
        flash("Agrega un título.", "warning")
        return redirect(url_for("tasks_page"))

    tasks_col.insert_one({
        "email": email,
        "title": title,
        "description": description,
        "completed": False
    })

    flash("Tarea agregada.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/tasks/toggle/<task_id>", methods=["POST"])
def toggle_task(task_id):
    if not current_user():
        return redirect(url_for("login"))

    task = tasks_col.find_one({"_id": ObjectId(task_id)})

    if task:
        tasks_col.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"completed": not task["completed"]}}
        )

    return redirect(url_for("tasks_page"))


@app.route("/tasks/delete/<task_id>", methods=["POST"])
def delete_task(task_id):
    if not current_user():
        return redirect(url_for("login"))

    tasks_col.delete_one({"_id": ObjectId(task_id)})

    flash("Tarea eliminada.", "success")
    return redirect(url_for("tasks_page"))


@app.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)