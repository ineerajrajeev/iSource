from flask import render_template, request, redirect, url_for, flash, session
from ..models import db, User, Questions, Organizations, Invites
from werkzeug.security import generate_password_hash, check_password_hash
from ..utils.role_check import role_required
from flask import Blueprint
from flask_dance.contrib.github import github

user_bpt = Blueprint('user', __name__)


@user_bpt.route('/github_login')
def github_login():
    if not github.authorized:
        flash(['Redirecting to login with github', 'info'])
        return redirect(url_for("github.login"))
    else:
        account_info = github.get('/user')
        if account_info.ok:
            account_info_json = account_info.json()
            id=account_info_json['login']
            user=User.query.filter_by(github_id=id).first()
            print(account_info_json)
            if user:
                session['user_id'] = user.userid
                flash(['User login successful!', 'success'])
                return redirect(url_for('user.user_dashboard'))
            else:
                flash('User not registered to for this github facility')
                return redirect(url_for('user.login'))

    flash('Failed to login with github')
    return redirect(url_for('user.login'))


# NOTE: This route takes to landing page
@user_bpt.route('/')
def index():
    flash(['Welcome to iHelp','success','Welcome','Welcome to iHelp'])
    
    return render_template('Landingpage.html',nav="Welcome")


@user_bpt.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        if User.query.filter_by(userid=session.get('user_id')).first().role == 'moderator':
            return redirect(url_for('moderator.moderator_dashboard'))
        return redirect(url_for('user.user_dashboard'))
    if session.get('org_id'):
        return redirect(url_for('organization.organization_dashboard'))
    if request.method == 'POST':
        role = request.form.get('role')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if role == 'user':
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.passhash, password):
                session['user_id'] = user.userid
                if user.role == 'moderator':
                    flash(['Moderator login successful!', 'success'])
                    return redirect(url_for('moderator.moderator_dashboard'))
                elif user.role == 'user':
                    flash(['User login successful!', 'success'])
                    return redirect(url_for('user.user_dashboard'))
            organization = Organizations.query.filter_by(orgemail=email).first()
            if organization:
                flash('Try switching to organization login')
            else:
                flash('Invalid user credentials. Please try again.')


        elif role == 'organization':
            organization = Organizations.query.filter_by(orgemail=email).first()
            if organization and check_password_hash(organization.orgpassword, password):
                session['org_id'] = organization.orgid
                flash(['Organization login successful!','success'])
                return redirect(url_for('organization.organization_dashboard'))
            flash('Invalid organization credentials. Please try again.')

    return render_template('login.html',nav="Login")


@user_bpt.route('/register',methods=["GET", "POST"])
def register(code=None, email=None):

    if request.method == 'GET':
        code = request.args.get('code')
        email = request.args.get('email')
        print(code)
    
    if request.method == 'POST':
        firstname=request.form.get('first_name')
        lastname=request.form.get('last_name')
        email=request.form.get('email')
        password=request.form.get('password')
        confirmpassword=request.form.get('confirmpassword')
        username=request.form.get('username')
        invitecode=request.form.get('invitecode')
        print(firstname,lastname,email,password,confirmpassword,username,invitecode)
        print(Invites.query.filter_by(code=invitecode).first())
        role=Invites.query.filter_by(code=invitecode).first().role

        if username is None or password is None or email is None or  firstname is None or lastname is None or invitecode is None:
            flash('Please fill the required fields')
            return redirect(url_for('user.register'))
        
        if password!=confirmpassword:
            flash('Passwords do not match')
            return redirect(url_for('user.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('user.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('user.register'))
        
        if not Invites.query.filter_by(code=invitecode).first():
            flash('Invalid invite code')
            return redirect(url_for('user.register'))
        
        invite = Invites.query.filter_by(code=invitecode).first()
        if invite.email != email:
            flash('Email does not match the invite code')
            return redirect(url_for('user.register'))
        
        orgid=invite.orgid
        if request.form.get('github_id'):
            github_id=request.form.get('github_id')
            user=User(firstname=firstname,lastname=lastname,username=username,
                  email=email,passhash=generate_password_hash(password),organization=orgid,role=role,github_id=github_id)
        else:
            user=User(firstname=firstname,lastname=lastname,username=username,
                    email=email,passhash=generate_password_hash(password),organization=orgid,role=role)
        invite.registered = True
        db.session.add(user)
        db.session.commit()
        flash(['You have successfully registered','success'])
        
        return redirect(url_for('user.login'))

    return render_template('register.html',code=code,email=email,nav="User Register")


@user_bpt.route('/dashboard/user')
@role_required("user")
def user_dashboard():

    questions=Questions.query.filter_by(userid=session['user_id']).order_by(Questions.date.desc()).limit(5).all()
    questions=[question.serializer() for question in questions]
    

    # questions = [
    #     {'id': 1, 'title': 'How to implement authentication in React?', 'short_description': 'I need to implement authentication...', 'time_ago': '2 hours', 'answer_count': 5, 'asker_name': 'John Doe'},
    #     {'id': 2, 'title': 'Best practices for React state management?', 'short_description': 'Looking for suggestions on managing state...', 'time_ago': '1 day', 'answer_count': 3, 'asker_name': 'Jane Smith'},
    #     {'id': 3, 'title': 'How to optimize React performance?', 'short_description': 'Performance optimization tips...', 'time_ago': '3 days', 'answer_count': 8, 'asker_name': 'Mark Lee'}
    # ]
    
    return render_template('user_dashboard.html', questions=questions,nav="User Dashboard")


@user_bpt.route('/myquestions',methods=['GET'])
@role_required('user')
def myquestions():
    questions=Questions.query.filter_by(userid=session['user_id']).order_by(Questions.date.desc()).all()
    questions=[question.serializer() for question in questions]
    return render_template('my_questions.html',questions=questions,nav="My Questions",role=User.query.filter_by(userid=session['user_id']).first().role)

