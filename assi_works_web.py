# 데이터베이스
import sqlite3
import pandas as pd

# 데이터 형식
from datetime import datetime

# 플라스크
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user, UserMixin
import requests
import os
import json

# 인증
from oauthlib.oauth2 import WebApplicationClient

with open('assi_works_app_config.json', 'r') as f:
    assi_works_app_config = json.load(f)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", assi_works_app_config['GOOGLE']['GOOGLE_CLIENT_ID'])
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", assi_works_app_config['GOOGLE']['GOOGLE_CLIENT_SECRET'])
GOOGLE_DISCOVERY_URL = (assi_works_app_config['GOOGLE']['GOOGLE_DISCOVERY_URL'])

# 애플리케이션
app = Flask(__name__)
app.secret_key = 'assi_works'

login_manager = LoginManager()
login_manager.init_app(app)

# OAuth2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# 계산 함수
def calc_assign_annual_leave_count(email, start_date):

    now  = datetime.now()
    date_diff = now - start_date

    if (start_date.year < now.year):
        return 15

    return (12 - start_date.month)

def calc_used_annual_leave_count(email):

    count = 0

    conn = sqlite3.connect('db/assi_works.db')
    curs = conn.cursor()
    query = curs.execute("SELECT date, hour, type, reason from annual_leave where email = ?", [email])

    df = pd.DataFrame.from_records(data=query.fetchall(), columns=['사용일', '시간', '타입', '사유'])
    
    for index, row in df.iterrows():
        if row['타입'] == '연차':
            if row['시간'] == '종일':
                count += 1
            elif row['시간'] == '오전' or row['시간'] == '오후':
                count += 0.5
    
    return df, count

def calc_holiday_work(email):

    #email = 'stella@aifactory.page'
    conn = sqlite3.connect('db/assi_works.db')
    curs = conn.cursor()
    query = curs.execute("SELECT date, dow, hour, reason from holiday_work where email = ?", [email])
    
    #cols = [column[0] for column in query.description]
    df = pd.DataFrame.from_records(data=query.fetchall(), columns=['근무일', '요일', '근무시간', '사유'])

    conn.close()

    df['보상시간'] = ''
    sum_work_hour = 0
    sum_reward_hour = 0

    for index, row in df.iterrows():
        work_hour = int(row['근무시간'])
        reward_hour = work_hour * 1.5
        df.at[index, '보상시간'] = reward_hour
        
        sum_work_hour += work_hour
        sum_reward_hour += reward_hour
    
    return df, sum_work_hour, sum_reward_hour

# 로그인

class User(UserMixin):
    def __init__(self, id, name, email, start_date, profile_pic):
        self.id = id
        self.name = name
        self.email = email
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.profile_pic = profile_pic
 
    @staticmethod
    def create(email, id, profile_pic):
        
        conn = sqlite3.connect('db/assi_works.db')
        curs = conn.cursor()

        curs.execute("SELECT * from user where email = ?", [email])
        lu = curs.fetchone()

        if lu is None:
            print("can't find email")
            return None

        curs.execute("UPDATE user SET uuid = ?, picture = ? WHERE email = ?", (id, profile_pic, email))
        conn.commit()
        conn.close()        

        return User.get(id)

    @staticmethod
    def get(id):
        
        conn = sqlite3.connect('db/assi_works.db')
        curs = conn.cursor()
        curs.execute("SELECT * from user where uuid = ?", [id])
        lu = curs.fetchone()
        conn.close()

        if lu is None:
            print("can't find unique_id")
            return None
        
        user = User(
            id   = lu[4], 
            name = lu[2],
            email = lu[1], 
            start_date = lu[3], 
            profile_pic = lu[5]
        )

        return user

# 플라스크 라우팅

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/', methods=['GET'])
@app.route('/index')
def index():

    print("current_user.is_authenticated:" +  str(current_user.is_authenticated))
    
    if current_user.is_authenticated != True:
        return render_template("login.html")

    assign_annual_leave_count = calc_assign_annual_leave_count(current_user.email, current_user.start_date)
    _, used_annual_leave_count = calc_used_annual_leave_count(current_user.email)

    meta = {'assign_annual_leave_count':assign_annual_leave_count,
            'used_annual_leave_count':used_annual_leave_count,
            'remain_annual_leave_count':assign_annual_leave_count - used_annual_leave_count}

    return render_template("index.html", meta = meta, current_user=current_user)

@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
 
    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route('/annual_leave')
@login_required
def annual_leave():
            
    assign_annual_leave_count = calc_assign_annual_leave_count(current_user.email, current_user.start_date)
    used_annual_leave_df, used_annual_leave_count = calc_used_annual_leave_count(current_user.email)

    meta = {'assign_annual_leave_count':assign_annual_leave_count,
            'used_annual_leave_count':used_annual_leave_count,
            'remain_annual_leave_count':assign_annual_leave_count - used_annual_leave_count}

    contents = used_annual_leave_df.to_html(index=False, classes = 'table table-bordered', table_id = 'dataTable')

    return render_template("annual_leave.html", meta=meta, contents=contents)


@app.route('/holiday_work')
@login_required
def holiday_work():

    holiday_work_df, sum_work_hour, sum_reward_hour = calc_holiday_work(current_user.email)

    meta = {'sum_work_hour':sum_work_hour,
            'sum_reward_hour':sum_reward_hour}

    contents = holiday_work_df.to_html(index=False, classes = 'table table-bordered', table_id = 'dataTable')

    return render_template("holiday_work.html", meta=meta, contents=contents)

@app.route('/alternative_holiday')
@login_required
def alternative_holiday():
    contents = []
    return render_template("alternative_holiday.html", contents=contents)

@app.route('/leave_request')
@login_required
def leave_request():
    contents = []
    return render_template("leave_request.html", contents=contents)

@app.route('/special_leave')
@login_required
def special_leave():
    contents = []
    return render_template("special_leave.html", contents=contents)

@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
 
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
 
    # Prepare and send request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )

    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
 
    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))
 
    # Now that we have tokens (yay) let's find and hit URL
    # from Google that gives you user's profile information,
    # including their Google Profile Image and Email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    print(userinfo_response.json())
 
    # We want to make sure their email is verified.
    # The user authenticated with Google, authorized our
    # app, and now we've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400
 
    user = User.get(unique_id)

    if not user:
        user = User.create(users_email, unique_id, picture)

        if not user:
            print("The email isn't registered.")
            return redirect(url_for("index"))        

    # Begin user session by logging the user in
    login_user(user, remember=True)
    # Send user back to homepage
    return redirect(url_for("index"))
 
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()       
 
@login_manager.unauthorized_handler
def unauthorized():
    return "You must be logged in to access this content.", 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4200, debug=True)
