from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, limiter
from app.models import User, notify_role
from app.utils import save_upload

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("8 per hour", methods=["POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip() or None
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        id_proof = request.files.get("id_proof")
        selfie = request.files.get("selfie")

        if not name or not phone or not address or not password:
            flash("Please fill in all required fields.", "error")
            return render_template("auth/signup.html")

        if User.query.filter_by(phone=phone).first():
            flash("An account with this phone number already exists.", "error")
            return render_template("auth/signup.html")

        if not id_proof or id_proof.filename == "":
            flash("Please upload a photo of your ID proof.", "error")
            return render_template("auth/signup.html")

        if not selfie or selfie.filename == "":
            flash("Please add a current photo of yourself — this helps staff confirm identity at pickup.", "error")
            return render_template("auth/signup.html")

        id_proof_path = save_upload(id_proof, current_app.config["ID_PROOF_FOLDER"], "id_proofs")
        if not id_proof_path:
            flash("ID proof must be a real PNG/JPG/WEBP image.", "error")
            return render_template("auth/signup.html")

        selfie_path = save_upload(selfie, current_app.config["SELFIE_FOLDER"], "selfies")
        if not selfie_path:
            flash("Your photo must be a real PNG/JPG/WEBP image.", "error")
            return render_template("auth/signup.html")

        user = User(
            role="customer",
            name=name,
            phone=phone,
            email=email,
            address=address,
            id_proof_path=id_proof_path,
            selfie_path=selfie_path,
            verification_status="PENDING",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        notify_role("admin", f"New signup: {user.name} needs ID review", link="/admin/customers?status=PENDING")
        db.session.commit()

        flash("Account created! An admin will review your ID proof before you can book a pickup.", "success")
        login_user(user)
        return redirect(url_for("customer.dashboard"))

    return render_template("auth/signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(phone=phone).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.index"))
        flash("Incorrect phone number or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
