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

# 환경설정 / 서비스
with open('assi_works_web_config.json', 'r') as f:
    assi_works_web_config = json.load(f)

# 환경설정 / 인증
with open('client_secret_key.json', 'r') as f:
    client_secret_key = json.load(f)

# 애플리케이션
app = Flask(__name__)
app.secret_key = 'assi_works'

login_manager = LoginManager()
login_manager.init_app(app)

client = WebApplicationClient(client_secret_key['web']['client_id'])

task_dict = {'task_general':'일반',
             'task_leave':'휴가'}
wot_dict = {'wot_request':'요청',
            'wot_confirm':'검토',
            'wot_execute':'집행',
            'wot_record':'기록',
            'wot_cc':'참조'}
wos_dict = {'wos_null':'생성',
            'wos_scheduled':'예정',
            'wos_wait':'대기',
            'wos_success':'성공',
            'wos_failure':'실패'}
wfs_dict = {'wfs_null':'생성',
            'wfs_scheduled':'예정',
            'wfs_wait':'대기',
            'wfs_success':'성공',
            'wfs_failure':'실패'}

def replace_code2word(df):
    df = df.replace(task_dict)
    df = df.replace(wot_dict)
    df = df.replace(wos_dict)
    df = df.replace(wfs_dict)
    return df

# 쿼리 함수
def get_user_list():
    
    conn = sqlite3.connect('db/assi_works.db')
    curs = conn.cursor()
    query = curs.execute("SELECT email, name from user")

    df = pd.DataFrame.from_records(data=query.fetchall(), columns=['이메일', '이름'])
    
    return df

def get_user_dict():
    
    df = get_user_list()

    return df.set_index('이메일')['이름'].to_dict()

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
            profile_pic = lu[6]
        )

        return user

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

def get_google_provider_cfg():
    return requests.get('https://accounts.google.com/.well-known/openid-configuration').json()       
 
@login_manager.unauthorized_handler
def unauthorized():
    return "You must be logged in to access this content.", 403

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
        auth=(client_secret_key['web']['client_id'], client_secret_key['web']['client_secret']),
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

# 플라스크 라우팅

@app.route('/', methods=['GET'])
@app.route('/index')
def index():

    print("current_user.is_authenticated:" +  str(current_user.is_authenticated))
    
    if current_user.is_authenticated != True:
        return render_template("login.html")
    '''
    assign_annual_leave_count = calc_assign_annual_leave_count(current_user.email, current_user.start_date)
    _, used_annual_leave_count = calc_used_annual_leave_count(current_user.email)
    '''

    meta = {'wos_scheduled_count':len(get_workorder_list(current_user.email, '0')),
            'wos_wait_count':len(get_workorder_list(current_user.email, '1'))}

    return render_template("index.html", meta = meta, current_user=current_user)

# 워크플로우

def add_workflow(workflow_creater_email, workflow_status, workorder_total_steps, task_type, task_id):
    
    conn = sqlite3.connect('db/assi_works.db')
    curs = conn.cursor()
    curs.execute("INSERT INTO workflow VALUES (null, '" + workflow_creater_email + "', '" + workflow_status + "', 1, " + str(workorder_total_steps) + ", '" + task_type + "', " + str(task_id) + ")")
    conn.commit()

    workflow_id = curs.lastrowid

    conn.close()

    return workflow_id

def add_workorder(workflow_id, workorder_type, workorder_status, workorder_step_seq, user_email, workorder_create_date, workorder_receive_date, workorder_complete_date, worker_comment):
    
    conn = sqlite3.connect('db/assi_works.db')
    curs = conn.cursor()
    curs.execute("INSERT INTO workorder VALUES (null, '" + str(workflow_id) + "' , '" + workorder_type + "', '" + workorder_status + "', " +  str(workorder_step_seq) + ", '" + user_email + "', '" + workorder_create_date + "', '" + workorder_receive_date + "', '" + workorder_complete_date + "', '" + worker_comment + "')")
    conn.commit()

    workorder_id = curs.lastrowid

    conn.close()

    return workorder_id

def get_workorder_list(user_email, workorder_status):

    conn = sqlite3.connect('db/assi_works.db')
    curs = conn.cursor()
    query = curs.execute("SELECT wo.id, wf.task_type, wf.task_id, wf.workflow_creater_email, wo.workorder_type, wo.workorder_step_seq, wf.workorder_curr_step_seq, wf.workorder_total_steps, wo.workorder_create_date, wo.workorder_receive_date, wo.workorder_complete_date, wo.worker_comment from workorder as wo INNER JOIN workflow AS wf ON wo.workflow_id = wf.id where wo.user_email = '" + user_email + "' and wo.workorder_status = '" + workorder_status + "'")

    df = pd.DataFrame.from_records(data=query.fetchall(), columns=['ID', '태스크', '태스크 ID', '발행', '액션', '순서', '현재', '전체', '생성일', '접수일', '완료일', '의견'])

    df = replace_code2word(df)
    df = df.replace(get_user_dict())

    conn.close()

    return df

@app.route('/workorder_scheduled')
@login_required
def workorder_scheduled():

    df = get_workorder_list(current_user.email, '0') # '0' scheduled
    df = df.drop(['태스크 ID', '접수일', '완료일', '의견'], axis=1)
    meta = {'item_name': '예정',
            'item_value': len(df)}
    contents = df.to_html(index=False, render_links=True, escape=False, classes = 'table table-bordered', table_id = 'dataTable')

    return render_template("workorder_list.html", meta=meta, contents=contents)

@app.route('/workorder_wait')
@login_required
def workorder_wait():

    df = get_workorder_list(current_user.email, '1') # '1' wait
    df = df.drop(['태스크 ID', '접수일', '완료일', '의견'], axis=1)
    meta = {'item_name': '대기',
            'item_value': len(df)}
    contents = df.to_html(index=False, render_links=True, escape=False, classes = 'table table-bordered', table_id = 'dataTable')

    return render_template("workorder_list.html", meta=meta, contents=contents)

@app.route('/workorder_success')
@login_required
def workorder_success():

    df = get_workorder_list(current_user.email, '2') # '2' success
    df = df.drop(['태스크 ID', '접수일', '완료일', '의견'], axis=1)
    meta = {'item_name': '성공',
            'item_value': len(df)}
    contents = df.to_html(index=False, render_links=True, escape=False, classes = 'table table-bordered', table_id = 'dataTable')

    return render_template("workorder_list.html", meta=meta, contents=contents)

@app.route('/workorder_failure')
@login_required
def workorder_failure():

    df = get_workorder_list(current_user.email, '3') # '3' failure
    df = df.drop(['태스크 ID', '접수일', '완료일', '의견'], axis=1)
    meta = {'item_name': '실패',
            'item_value': len(df)}
    contents = df.to_html(index=False, render_links=True, escape=False, classes = 'table table-bordered', table_id = 'dataTable')

    return render_template("workorder_list.html", meta=meta, contents=contents)

# 일반 업무

# general_leave - form
@app.route('/task_general_request_form')
@login_required
def task_general_request_form():
    contents = []
    prefill_workflow = []
    prefill_workflow_contents = []

    user_list = get_user_list().values.tolist()

    return render_template("task_general_request_form.html", contents=contents, prefill_workflow_contents=prefill_workflow_contents, workorder_type_list = list(wot_dict.items()), user_list = user_list)

@app.route('/task_general_request', methods = ['POST'])
@login_required
def task_general_request():

    if request.method == 'POST':
        data = request.form

    return render_template('form_recv.html', data = data)

# 휴가

def insert_annual_leave_task(user_email, use_date, leave_use_date, leave_type, leave_reason):
    
    conn = sqlite3.connect('db/assi_works.db')
    curs = conn.cursor()
    curs.execute("INSERT INTO annual_leave_task VALUES (null, '" + user_email + "', '" + use_date + "', '" + leave_use_date + "', '" + leave_type + "', '" + leave_reason + "')")
    conn.commit()
    task_id = curs.lastrowid
    conn.close()
    
    return task_id

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

@app.route('/special_leave')
@login_required
def special_leave():
    contents = []
    return render_template("special_leave.html", contents=contents)

# task_leave - form
@app.route('/task_leave_request_form')
@login_required
def task_leave_request_form():
    contents = []
    prefill_workflow = []
    prefill_workflow_contents = []

    user_list = get_user_list().values.tolist()

    return render_template("task_leave_request_form.html", contents=contents, prefill_workflow_contents=prefill_workflow_contents, workorder_type_list = list(wot_dict.items()), user_list = user_list)

@app.route('/task_leave_request', methods = ['POST'])
@login_required
def task_leave_request():

    if request.method == 'POST':
        data = request.form

    return render_template('form_recv.html', data = data)
    #return redirect(url_for("annual_leave"))    
'''
    # 예정 > 대기 > 입력
    add_workorder(workflow_id, 'fill', '대기', 1, user_email, curr_time, curr_time, '', '')
    
    # 예정 > 대기 > 승인|반려
    add_workorder(workflow_id, 'confirm', '예정', 2, 'song@aifactory.page', curr_time, '', '', '')
'''
if __name__ == '__main__':
    app.run(host=assi_works_web_config['service_host'], port=assi_works_web_config['service_port'], ssl_context=assi_works_web_config['service_ssl_context'])