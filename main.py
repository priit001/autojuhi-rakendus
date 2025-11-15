from flask import Flask, request, render_template_string
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>Tere tulemast autojuhi rakendusse!</h1>
    <p><a href="/register">Registreeri</a> | <a href="/login">Logi sisse</a></p>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kasutajanimi = request.form['username']
        parool = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute('SELECT password FROM users WHERE username = ?', (kasutajanimi,))
        result = cursor.fetchone()
        conn.close()

        if result and check_password_hash(result[0], parool):

            return f"<h2>Tere tulemast, {kasutajanimi}!</h2>"
        else:
            return "<h2>Vale kasutajanimi või parool.</h2>"

    login_form = '''
    <h2>Logi sisse</h2>
    <form method="POST">
        <label>Kasutajanimi:</label><br>
        <input type="text" name="username"><br><br>
        <label>Parool:</label><br>
        <input type="password" name="password"><br><br>
        <input type="submit" value="Logi sisse">
    </form>
    '''
    return render_template_string(login_form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uus_kasutaja = request.form['username']
        uus_parool = generate_password_hash(request.form['password'])



        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (uus_kasutaja, uus_parool))
            conn.commit()
            message = f"<h2>Kasutaja {uus_kasutaja} registreeritud!</h2>"
        except sqlite3.IntegrityError:
            message = f"<h2>Kasutajanimi '{uus_kasutaja}' on juba kasutusel.</h2>"

        conn.close()
        return message

    register_form = '''
    <h2>Registreeri uus kasutaja</h2>
    <form method="POST">
        <label>Kasutajanimi:</label><br>
        <input type="text" name="username"><br><br>
        <label>Parool:</label><br>
        <input type="password" name="password"><br><br>
        <input type="submit" value="Registreeri">
    </form>
    '''
    return render_template_string(register_form)

if __name__ == '__main__':
    app.run(debug=True)
