from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
import pandas as pd
import os
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'fixed_secret_key_12345'  # 改为固定密钥维持会话持久性

# 邮箱配置
app.config['MAIL_SERVER'] = 'smtp.qiye.aliyun.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'AlexPeng@careerintlinc.com'
app.config['MAIL_PASSWORD'] = 'N651LvEanhgDUpXP'

# 文件存储路径
USERS_FILE = 'users.xlsx'
ACCOUNTS_FILE = 'accounts.xlsx'
LOGS_FILE = 'logs.xlsx'

# 初始化邮箱
try:
    mail = Mail(app)
except Exception as e:
    print(f'邮件初始化失败: {str(e)}')

# 定时任务
scheduler = BackgroundScheduler()

# 创建初始Excel文件（如果不存在）
for f in [USERS_FILE, ACCOUNTS_FILE, LOGS_FILE]:
    if not os.path.exists(f):
        pd.DataFrame(columns=['账号','密码']).to_excel(USERS_FILE, index=False)
        pd.DataFrame(columns=['账号','密码','已发送']).to_excel(ACCOUNTS_FILE, index=False) 
        pd.DataFrame(columns=['时间','用户','操作']).to_excel(LOGS_FILE, index=False)

# 计划任务：每天20点发送日志
@scheduler.scheduled_job('cron', hour=20)
def send_daily_logs():
    # 实现日志发送逻辑
    pass

scheduler.start()

@app.route('/', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return render_template('login.html', error='请输入账号和密码')
    
    try:
        df = pd.read_excel(USERS_FILE, engine='openpyxl')
        user = df[(df['账号'] == username) & (df['密码'] == password)]
        
        if not user.empty:
            session['username'] = username
            # 管理员检测逻辑
            if username == 'admin':
                session['admin'] = True
            flash('登录成功', 'success')
            return redirect(url_for('submit_page'))
        else:
            return render_template('login.html', error='账号或密码错误')
    except Exception as e:
        print(f'登录错误: {str(e)}')
        return render_template('login.html', error='系统错误，请稍后重试')

@app.route('/submit')
def submit_page():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template('submit_info.html')

@app.route('/submit', methods=['POST'])
def handle_submit():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    
    name = request.form['name']
    email = request.form['email']
    
    try:
        # 获取可用账号
        accounts_df = pd.read_excel(ACCOUNTS_FILE)
        available = accounts_df[accounts_df['已发送'] == False].iloc[0]
        
        # 发送邮件
        msg = Message('综合测评', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"账号：{available['账号']}\n密码：{available['密码']}"
        mail.send(msg)
        
        # 更新账户状态
        accounts_df.at[available.name, '已发送'] = True
        accounts_df.to_excel(ACCOUNTS_FILE, index=False)
        
        # 记录日志
        log_df = pd.read_excel(LOGS_FILE)
        new_log = pd.DataFrame([{
            '时间': pd.Timestamp.now(),
            '用户': session['username'],
            '操作': f'发送账号至{email}'
        }])
        log_df = pd.concat([log_df, new_log])
        log_df.to_excel(LOGS_FILE, index=False)
        
    except Exception as e:
        print(f'提交错误: {str(e)}')
        flash('提交失败，请重试', 'error')
        return redirect(url_for('submit_page'))
    
    flash('提交成功！账号信息已发送至您的邮箱', 'success')
    return redirect(url_for('submit_page'))

@app.route('/admin')
def admin_page():
    if 'admin' not in session:
        return redirect(url_for('login_page'))
    return render_template('admin.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    if 'admin' not in session:
        return redirect(url_for('login_page'))
    
    try:
        file = request.files['accounts_file']
        # 验证文件格式
        required_columns = ['账号', '密码']
        new_df = pd.read_excel(file)
        if not all(col in new_df.columns for col in required_columns):
            return render_template('admin.html', error='文件必须包含账号和密码列')
        
        # 合并新账号
        existing_df = pd.read_excel(ACCOUNTS_FILE)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df['已发送'] = combined_df['已发送'].fillna(False)
        
        # 去重处理
        final_df = combined_df.drop_duplicates(subset=['账号'], keep='last')
        final_df.to_excel(ACCOUNTS_FILE, index=False)
        
        # 检查库存并发送预警
        available_count = len(final_df[final_df['已发送'] == False])
        if available_count < 10:
            send_alert_email(available_count)
        
    except Exception as e:
        print(f'文件上传错误: {str(e)}')
        return render_template('admin.html', error='文件格式错误')
    
    flash(f'成功新增{len(new_df)}个账号', 'success')
    return redirect(url_for('admin_page'))

def send_alert_email(count):
    try:
        msg = Message('库存预警', sender=app.config['MAIL_USERNAME'], recipients=['pq2008317@163.com'])
        msg.body = f"剩余可用账号数量：{count}，请及时补充！"
        mail.send(msg)
    except Exception as e:
        print(f'预警邮件发送失败: {str(e)}')

# 完善定时任务
@scheduler.scheduled_job('cron', hour=20)
def send_daily_logs():
    try:
        # 生成日志文件
        log_df = pd.read_excel(LOGS_FILE)
        today = pd.Timestamp.now().strftime('%Y-%m-%d')
        daily_logs = log_df[log_df['时间'].dt.date == pd.Timestamp.now().date()]
        
        # 创建邮件
        msg = Message('每日日志报告', 
                     sender=app.config['MAIL_USERNAME'],
                     recipients=['alex533@vip.163.com'],
                     cc=['pq2008317@163.com'])
        msg.body = '附件为当日操作日志'
        
        # 添加Excel附件
        with app.open_resource(LOGS_FILE) as fp:
            msg.attach('daily_log.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', fp.read())
        
        mail.send(msg)
    except Exception as e:
        print(f'日志发送失败: {str(e)}')

# 新增用户数据保存功能
try:
    user_df = pd.read_excel(USERS_FILE, engine='openpyxl')
    
    # 添加测试账户
    test_account = pd.DataFrame([{'账号': 'test2024', '密码': 'Test@2024'}])
    user_df = pd.concat([user_df, test_account], ignore_index=True)
    user_df.drop_duplicates(subset=['账号'], keep='last', inplace=True)
    user_df.to_excel(USERS_FILE, index=False, engine='openpyxl')
except Exception as e:
    print(f'保存用户数据时出错: {e}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)