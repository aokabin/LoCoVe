# ! /usr/bin/python
# -*- coding: utf-8 -*- 

# all the imports
from __future__ import with_statement
from flask import Flask, request, session, g, redirect, url_for, \
	 abort, render_template, flash
from pymongo import Connection
import hashlib
import smtplib
from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import formatdate
import datetime
import locale

# configuration
# DATABASE = 'flasker.db'
DEBUG = True
SECRET_KEY = 'development key'
# USERNAME = 'admin'
# PASSWORD = 'default'
# CON = Connection('localhost', 27017)
ADDRESS = 'info@lowcost-vehicle.com'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKER_SETTINGS', silent=True)

"""
def connect_db():
	return sqlite3.connect(app.config['DATABASE'])

def init_db():
	with closing(connect_db()) as db:
		with app.open_resource('locove.sql') as f:
			db.cursor().executescript(f.read())
		db.commit()
"""

def connect_db():
	con = Connection('localhost', 27017)
	return con

@app.before_request
def before_request():
	g.con = connect_db()

@app.teardown_request
def teardown_request(exception):
	g.con.disconnect()

@app.route('/')
def show_entries():
	db = g.con.locove
	col = db.entries
	dri_ent = []
	rid_ent = []

	for ent in col.find({'enttype' : 0}):
		dri_ent.append(ent)

	for ent in col.find({'enttype' : 1}):
		rid_ent.append(ent)
	
	#cur = g.db.execute('select title, text from entries order by id desc')
	return render_template('show_entries.html', dri_ent=dri_ent, rid_ent=rid_ent)



@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	if session.get('logged_in') != None:
		return redirect(url_for('show_entries'))
	if request.method =='POST':
		db = g.con.locove
		col = db.usr
		usr_id = request.form['usrid']
		data = col.find_one({'usrid' : usr_id})
		pw = hashlib.sha224(request.form['usrpw']).hexdigest()
		if data != None :
			if data['usrpw'] == pw and data['usrcheck']:
				session['logged_in'] = data['usrid']
				flash('You were logged in')
				return render_template('mypage.html', data=data)
			return redirect(url_for('login'))
	return render_template('login.html', error=error)

@app.route('/logout')
def logout():
	session.pop('logged_in', None)
	flash('You were logged out')
	return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def  signup():
	error = None
	if session.get('logged_in') != None:
		abort(401)
	if request.method == 'POST':
		db = g.con.locove
		col = db.usr
		usrid = col.find({'usrid' : request.form['usrid']})
		usrmail = col.find({'usrmail' : request.form['usrmail']})
		if list(usrid) and list(usrmail):
			flash('Not unique your id or email.')
			error = 'Your acount is not unique.'
			return render_template('signup.html', error=error)
		
		# data = col.find_one({'usrid' : request.form['usrid']})
		# session['logged_in'] = data['usrid']
		# return render_template('mypage.html', data=data)
		to_address = request.form['usrmail']
		email = to_address
		charset = 'ISO-2022-JP'
		subject = u'本登録用メール'
		url =  hashlib.sha224(request.form['usrmail']).hexdigest()
		text =  u'以下のリンクが本登録のためのURLとなります。\n' + 'http://localhost:5000/entry?makeshift=' + url + u'\nリンクをクリックすれば本登録完了となります。'

		msg = MIMEText(text.encode(charset),"plain",charset)
		msg['Subject'] = Header(subject, charset)
		msg['From'] = ADDRESS
		msg['To'] = to_address
		msg['Date'] = formatdate(localtime = True)

		smtp = smtplib.SMTP_SSL('smtp.lolipop.jp', 465)
		smtp.ehlo('info@lowcost-vehicle.com')
		smtp.login('info@lowcost-vehicle.com', 'uvcfcb')
		smtp.sendmail(ADDRESS,to_address,msg.as_string())
		smtp.close()

		pw = hashlib.sha224(request.form['usrpw']).hexdigest()
		col2 = db.makeshift
		col2.insert({'usrid' : request.form['usrid'], 'makeshift' : url})
		col.insert({'usrid' : request.form['usrid'], 'usrpw' : pw, 'usrmail' : request.form['usrmail'], 'usrcheck' : False, 'usrtype' : 0})
		# usrtype = 1 have a car
		flash('Created Your Acount!')
		return render_template('makeshift.html', email=email)
	print 'get get'
	return render_template('signup.html', error=error)

@app.route('/entry')
def entry():
	if session.get('logged_in') != None:
		abort(401)

	if request.method == 'GET':
		db = g.con.locove
		col = db.usr
		col2 = db.makeshift

		makeshift = col2.find({'makeshift' : request.args.get('makeshift', '')})

		if not list(makeshift):
			flash('Your Account is Noting.')	
			return redirect(url_for('show_entries'))

		flash('Your Account Created!')	
		makeshift = col2.find_one({'makeshift' : request.args.get('makeshift', '')})
		account = col.find_one({'usrid' : makeshift['usrid']})
		account['usrcheck'] = True
		col2.remove({'makeshift' : request.args.get('makeshift', '')})
		col.save(account)
		return redirect(url_for('login'))

	return redirect(url_for('show_entries'))	

@app.route('/user')
def user():
	error = None
	if session.get('logged_in') == None:
		abort(401)

	db = g.con.locove
	col = db.entries

	entry = request.args.get('usercode', '')
	page = col.find_one({'query' : entry})
	if entry == '':
		print 'entry none'
		return render_template('mypage.html', error=error)
	else :
		session['usercode'] = request.args.get('usercode' , '')
		return render_template('info.html', page=page)

@app.route('/ask', methods=['POST'])
def ask():
	if session.get('logged_in') == None or session.get('usercode') == None:
		abort(401)
	db = g.con.locove
	col = db.entries
	session.pop('usercode', None)
	for i in range(1,10):
		ch = "rider"
		key = ch + str(i)
		update = col.find_one({'query' : request.form['fique'], key : {'$exists' : False}})
		if update != None:
			update[key] = session.get('logged_in')
			col.save(update)
			flash('Asked Your riding!')
			return redirect(url_for('show_entries'))
	flash('Your Ask is faild!')
	return redirect(url_for('show_entries'))

@app.route('/mypage')
def mypage():
	error = None
	if session.get('logged_in') == None:
		abort(401)

	return render_template('mypage.html', error=error)

@app.route('/rider', methods=['POST', 'GET'])
def rider():
	error =None
	now = datetime.datetime.today()
	if session.get('logged_in') == None:
		abort(401)
	if request.method == 'POST':
		db = g.con.locove
		col = db.entries
		que = hashlib.sha224((str(now) + str(session.get('logged_in')))).hexdigest()
		col.insert({'usrid' : session.get('logged_in'), 'destination' : request.form['destination'], 'board' : request.form['board'], 'time' : request.form['boardtime'], 'timestamp' : now, 'query' : que, 'enttype' : 0})
		# enttype = 0 rider 1 driver
		return redirect(url_for('mypage'))
	return render_template('rider.html', error=error)


@app.route('/driver', methods=['POST', 'GET'])
def driver():
	error =None
	now = datetime.datetime.today()
	if session.get('logged_in') == None:
		abort(401)
	if request.method == 'POST':
		db = g.con.locove
		col = db.entries
		que = hashlib.sha224((str(now) + str(session.get('logged_in')))).hexdigest()
		col.insert({'usrid' : session.get('logged_in'), 'destination' : request.form['destination'], 'board' : request.form['board'], 'time' : request.form['boardtime'], 'timestamp' : now, 'query' : que, 'enttype' : 1})
		return redirect(url_for('mypage'))
	return render_template('driver.html', error=error)

@app.route('/setting', methods=['POST', 'GET'])
def setting():
	error = None
	if session.get('logged_in') == None:
		abort(401)
	if request.method == 'POST':
		db = g.con.locove
		col = db.usr
		setdata = col.find_one({'usrid' : session.get('logged_in')})
		if list(setdata):
			flash('Please relogin!')
			return redirect(url_for('login'))
		setdata['kanji'] = request.form['kanji']
		setdata['rome'] = request.form['rome']
		setdata['school'] = request.form['school']
		setdata['havecar'] = request.form['havecar']
		if request.form['havecar'] == 1:
			setdata['carnum'] = request.form['carnum']
			setdata['carhira'] = request.form['carhira']

		setdata['introduce'] = request.form['introduce']
		flash('Your infomation is updated!')
		return redirect(url_for('user'))

	return render_template('setting.html', error=error)

# @app.route('/setting', methods=['POST'])
# def setting():
# 	error = None
# 	if  session.get('logged_in') == None:
# 		abort(401)
# 	if request.method == 'POST':
# 		db = g.con.locove
# 		col = db.usr
# 		data = col.find_one({'usrid' : session['logged_in']})

# 	return render_template('mypage.html', error=error)

if __name__ == '__main__':
	#init_db()
	app.run()

