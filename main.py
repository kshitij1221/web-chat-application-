from flask import Flask, render_template, request, session, jsonify, redirect, url_for, send_from_directory, make_response
from flask_socketio import join_room, leave_room, send, SocketIO, emit
from werkzeug.utils import secure_filename
from flask_login import current_user, login_user, login_required, logout_user, LoginManager, UserMixin
from flask_mail import Mail, Message
from db import save_user, get_user, User
import os
import random
from string import ascii_uppercase
from twilio.rest import Client



app = Flask(__name__)
# Initialize Twilio client
# account_sid = os.getenv('TWILIO_ACCOUNT_SID')
# auth_token = os.getenv('TWILIO_AUTH_TOKEN')
# twilio_client = Client(account_sid, auth_token)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["SECRET_KEY"] = "hjhjsdahhds"
app.config["SESSION_TYPE"] = "filesystem"
socketio = SocketIO(app)

app.config['MAIL_SERVER'] = 'sandbox.smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = '9ab63c59e25490'
app.config['MAIL_PASSWORD'] = 'fbea2817b59302'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


rooms = {}

def generate_unique_code(length=4):
    while True:
        code = ''.join(random.choices(ascii_uppercase, k=length))
        if code not in rooms:
            return code

@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)

@app.route("/", methods=["POST", "GET"])
@login_required
def home():
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        
        response = make_response(redirect(url_for("room")))
        response.set_cookie("room", room)
        response.set_cookie("name", name)
        return response
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        if not username or not email or not password:
            return render_template("signup.html", error="Please enter all fields.")

        user = get_user(username)
        if user:
            return render_template("signup.html", error="Username already exists.")

        save_user(username, email, password)
        user = get_user(username)
        login_user(user)
        return redirect(url_for("home"))
    
    return render_template("signup.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            return render_template("login.html", error="Please enter both username and password.")

        user = get_user(username)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid username or password.")
    
    return render_template("login.html")

@app.route("/room")
@login_required
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    content = {"name": session.get("name"), "message": data["data"]}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("media")
def handle_media(data):
    room = session.get("room")
    if room not in rooms:
        return 
    content = {"name": session.get("name"), "url": data["url"]}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} shared media: {data['url']}")

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    session['name'] = username
    session['room'] = room

    if room not in rooms:
        rooms[room] = {"members": 0, "messages": []}

    # Notify other members in the room
    send({"name": username, "message": "has entered the room."}, to=room)

    # Send the chat history to the new member
    emit("load_messages", {"messages": rooms[room]['messages']}, room=request.sid)

    rooms[room]["members"] += 1
    print(f"{username} joined room {room}")


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

@app.route("/send_invites", methods=["POST"])
@login_required
def send_invites():
    emails = request.form.getlist("emails")
    room_code = session.get("room")
    name = session.get("name")
    if not emails or not room_code:
        return render_template("home.html", error="Please provide email addresses and make sure you are in a room.")
    for email in emails:
        msg = Message('Room Invitation', sender='your-email@example.com', recipients=[email])
        msg.body = f"You have been invited by {name} to join the room with code: {room_code}"
        mail.send(msg)
    return redirect(url_for("room"))

@app.route("/exit_chat", methods=["POST"])
@login_required
def exit_chat():
    session.pop("room", None)
    session.pop("name", None)
    return jsonify({"success": True})

@app.route('/upload_media', methods=['POST'])
@login_required
def upload_media():
    if 'media' not in request.files:
        return jsonify(success=False, message="No file part")
    file = request.files['media']
    if file.filename == '':
        return jsonify(success=False, message="No selected file")
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        # Assuming the app is running locally and the files are accessible at /uploads/filename
        file_url = url_for('uploaded_file', filename=filename)
        return jsonify(success=True, url=file_url)
    return jsonify(success=False, message="File upload failed")

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# @app.route('/make_call', methods=['POST'])
# @login_required
# def make_call():
#     to_number = request.form.get('to_number')
#     if not to_number:
#         return jsonify(success=False, message="Recipient phone number is required")

#     from_number = os.getenv('TWILIO_PHONE_NUMBER')

#     try:
#         call = twilio_client.calls.create(
#             to=to_number,
#             from_=from_number,
#             url="http://demo.twilio.com/docs/voice.xml"
#         )
#         return jsonify(success=True, call_sid=call.sid)
#     except Exception as e:
#         return jsonify(success=False, message=str(e))



# @socketio.on('offer')
# def handle_offer(data):
#     emit('offer', data, broadcast=True)

# @socketio.on('answer')
# def handle_answer(data):
#     emit('answer', data, broadcast=True)

# @socketio.on('ice-candidate')
# def handle_ice_candidate(data):
#     emit('ice-candidate', data, broadcast=True)
if __name__ == "__main__":
    socketio.run(app, debug=True)

