from flask import Flask, render_template, session, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField
from wtforms.validators import DataRequired, Length, ValidationError
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("URI")
socketio = SocketIO(app)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    messages = db.relationship('Message', back_populates='user')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    user = db.relationship('User', back_populates='messages')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@app.before_first_request
def create_tables():
    db.create_all()

def is_nick_exist(form, field):
    if db.session.query(User).filter(User.name == field.data).first():
        raise ValidationError('This nickname is taken')

class RegForm(FlaskForm):
    name = StringField('Nickname', validators=[DataRequired(), Length(min=1, max=10), is_nick_exist])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=1, max=10)])
    submit = SubmitField('Submit')
class LogForm(FlaskForm):
    name = StringField('Nickname', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')



@app.route('/')
def index():
    if session.get('name') == None:
        return redirect(url_for('login'))
    return render_template('session.html', messages=db.session.query(Message).all()[-100:])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('name') != None:
        return redirect(url_for('index'))
    form = RegForm()
    if form.validate_on_submit():
        db.session.add(User(name=form.name.data, password=form.password.data))
        db.session.commit()
        session['name'] = form.name.data
        return redirect(url_for('index'))
    return render_template('auth.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('name') != None:
        return redirect(url_for('index'))
    form = LogForm()
    if form.validate_on_submit():
        usr = db.session.query(User).filter(User.name == form.name.data).first()
        if usr == None:
            flash('This name is not registered')
            return redirect(url_for('login'))
        elif usr.password == form.password.data:
            session['name'] = form.name.data
            return redirect(url_for('index'))
        else:
            flash('Name or password is incorrect')
            return redirect(url_for('login'))

    return render_template('auth.html', form=form)



@app.route('/logout')
def logout():
    session.pop("name")
    return redirect(url_for('login'))

def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')


@socketio.on('my event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    print('received my event: ' + str(json))
    if 'message' in str(json):
        mes = Message(text=json['message'], user_id=db.session.query(User).filter(User.name == session.get('name')).first().id)
        db.session.add(mes)
        db.session.commit()
    json['name'] = session.get('name')
    socketio.emit('my response', json, callback=messageReceived)



if __name__ == '__main__':
    socketio.run(app, debug=True)