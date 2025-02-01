import datetime
from ..models import db, User, Questions, Answers, Organizations, Invites, Docs
from flask import request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash
import random
import string
from ..utils.role_check import role_required
from ..utils.other import generate_demo_data
from flask import Blueprint
import threading
from ..utils.email_notification import send_email

organization_bpt = Blueprint('organization', __name__)


@organization_bpt.route('/register/organization',methods=["GET", "POST"])
def OrganizationRegister():

    if request.method == 'POST':
        orgname = request.form.get('orgname')
        orgemail = request.form.get('orgemail')
        orgphone = request.form.get('orgphone')
        orgpassword = request.form.get('orgpassword')
        confirmpassword = request.form.get('confirmpassword')
        orgwebsite = request.form.get('orgwebsite')
        orgtype = request.form.get('orgtype')
        orgdesc = request.form.get('orgdesc')
        created_at = datetime.datetime.now()
        orglogo = request.files['orglogo'].read()

        if orgname is None or orgemail is None or orgpassword is None or confirmpassword is None or orgwebsite is None:
            flash('Please fill the required fields')
            return redirect(url_for('organization.OrganizationRegister'))
        elif orgpassword!=confirmpassword:
            flash('Passwords do not match')
            return redirect(url_for('organization.OrganizationRegister'))
        elif Organizations.query.filter_by(orgemail=orgemail).first():
            flash('Email already exists')
            return redirect(url_for('organization.OrganizationRegister'))
        else:
            organization=Organizations(orgname=orgname,orglogo=orglogo,orgemail=orgemail,orgphone=orgphone,
                                       orgpassword=generate_password_hash(orgpassword),orgwebsite=orgwebsite,orgtype=orgtype,orgdesc=orgdesc,created_at=created_at)
            db.session.add(organization)
            db.session.commit()
            flash(['You have successfully registered','success'])
            return redirect(url_for('user.login'))

    return render_template('organizationRegister.html',nav="Organization Register")


# NOTE: Organization dashboard
@organization_bpt.route('/dashboard/organization')
@role_required('organization')
def organization_dashboard():
    # Get last 5 questions for organization
    questions = []
    ques = Questions.query.filter_by(orgid=session['org_id']).order_by(Questions.date.desc()).limit(3).all()
    for que in ques:
        questions.append(que.serializer())


    pdf_files = Docs.query.filter_by(orgid=session['org_id']).all()
    pdf_files_serialized = [doc.serializer() for doc in pdf_files]
    all_invites = []

    # top 5 user having role user and moderator
    top_5_user = Invites.query.filter(Invites.registered == True and Invites.orgid == session.get('org_id')).order_by(Invites.date.desc()).limit(5).all()
    top_5_moderator = Invites.query.filter(Invites.registered == False and Invites.orgid == session.get('org_id')).order_by(Invites.date.desc()).limit(5).all()
    print(top_5_user, top_5_moderator)

    for invite in top_5_user:
        if invite.orgid == session.get('org_id'):
            all_invites.append(invite.serializer())
        
    for invite in top_5_moderator:
        if invite.orgid == session.get('org_id'):
            all_invites.append(invite.serializer())

    total_invites=len(all_invites)

    total_users=User.query.filter_by(organization=session['org_id']).count()
    user = User.query.filter_by(organization=session['org_id']).all()
    total_answers=0
    total_questions=Questions.query.filter_by(orgid=session['org_id']).count()
    for user in user:
        total_answers = total_answers+Answers.query.filter_by(userid=user.userid).count()
    content={'total_users':total_users,'total_questions':total_questions,'total_answers':total_answers}

    return render_template(
                            'OrganizationDashboard.html',
                            data=generate_demo_data(),
                            questions=questions,
                            invites=all_invites,
                            nav="Organization Dashboard",
                            content=content,
                            pdf_files=pdf_files_serialized,
                            total_invites=total_invites
                        )


@organization_bpt.route('/invite_user',methods=["POST"])
@role_required('organization')
def inviteUser():
    email = request.form.get('email')
    role = request.form.get('role')
    orgid = session.get('org_id')
    date = datetime.datetime.now()

    if email is None or role is None:
        flash('Please fill the required fields')
        return redirect(url_for('organization.userManager'))
    elif Invites.query.filter_by(email=email).first():
        flash('Email already exists')
        return redirect(url_for('organization.userManager'))

    characters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(characters) for _ in range(16))

    # Format the code as XXXX XXXX XXXX XXXX
    code = ' '.join([code[i:i+4] for i in range(0, len(code), 4)])

    print(email,role,code)
    invite = Invites(email=email,role=role,code=code,orgid=orgid,date=date)
    db.session.add(invite)
    db.session.commit()
    flash(['Invited successfully','success'])
    register_url=url_for('user.register', code=code,email=email, _external=True)
    browser_url = url_for('organization.invitedmail', code=code,email=email,role=role, _external=True)
    print(register_url)

    # email sent part 
    email = email
    print(email)
    subject = "You've been invited to join iHelp"

    body = render_template('emailinvite.html',email=email,code=code,role=role,register_url=register_url,browser_url=browser_url)

    # Start a new thread to send the email
    thread = threading.Thread(target=send_email, args=(email, subject, body))
    thread.start()
    flash(['Mail sent successfully','success'])

    return redirect(url_for('organization.userManager'))


@organization_bpt.route('/invitedmail')
def invitedmail(email=None,code=None,role=None):
    email = request.args.get('email')
    code = request.args.get('code')
    role = request.args.get('role')
    print(email,code,role)
    # browser user
    if not (email is None and code is None and role is None):
        register_url=url_for('user.register', code=code,email=email, _external=True)
        return render_template('emailinvite.html',email=email,code=code,role=role,register_url=register_url,browser_url=None)
    # email user
    else:
        register_url=url_for('user.register', code="1234 5678 9012 3456",email="demo@gmail.com", _external=True)
        browser_url = url_for('organization.invitedmail', code="1234 5678 9012 3456",email="demo@gmail.com",role="admin", _external=True)
        return render_template('emailinvite.html',email="demo@gmail.com",code="1234 5678 9012 3456",role="admin",register_url=register_url,browser_url=browser_url)


@organization_bpt.route('/UserManager')
@role_required('organization')
def userManager():
    invites = Invites.query.filter_by(orgid=session.get('org_id')).all()
    print(session.get('org_id'))
    print(datetime.datetime.now())
    characters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(characters) for _ in range(16))
    print(code)
    all_invites = []
    for invite in invites:
        all_invites.append(invite.serializer())
    return render_template('OrgUserManager.html',invites=all_invites,nav="User Manager")


@organization_bpt.route('/UserManager', methods=['POST'])
@role_required('organization')
def UserManager():
    try:
        # Get JSON data
        data = request.get_json()
        print(data)
        print(type(data.get('registered')))
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        if not data.get('email'):
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        if not data.get('orgid'):
            return jsonify({'success': False, 'message': 'Organization ID is required'}), 400
        if not data.get('role'):
            return jsonify({'success': False, 'message': 'Role is required'}), 400
        if not data.get('code'):
            return jsonify({'success': False, 'message': 'Code is required'}), 400
        if data.get('new_password') != data.get('confirm_password'):
            return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        try:
            orgid=str(Organizations.query.filter_by(orgid=data.get('orgid')).first().orgid)
        except:
            return jsonify({'success': False, 'message': 'Organization not found'}), 404
        if data.get('orgid') != orgid:
            return jsonify({'success': False, 'message': 'Organization not found'}), 404
        if data.get('registered') == 'False' and data.get('new_password') is not None or data.get('confirm_password') is not None:
            return jsonify({'success': False, 'message': 'Password is not required for unregistered users'}), 400
        if data.get('id') is None:
            return jsonify({'success': False, 'message': 'ID is required'}), 400
        
        if data.get('registered') == 'True':
            print('True')
            user = User.query.filter_by(userid=data['id']).first()
            user.email = data.get('email')
            user.orgid = data.get('orgid')
            invite = Invites.query.filter_by(inviteid=data['id']).first()
            invite.email = data.get('email')
            invite.role = data.get('role')
            invite.orgid = data.get('orgid')
            
            if data.get('new_password'):
                user.password = generate_password_hash(data.get('new_password'))

        elif data.get('registered') == 'False':
            print('False')
            invite = Invites.query.filter_by(inviteid=data['id']).first()
            invite.email = data.get('email')
            invite.role = data.get('role')
            invite.orgid = data.get('orgid')
            
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@organization_bpt.route('/UserManager', methods=['DELETE'])
@role_required('organization')
def UserManager_delete():
    print(request.get_json())
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    if not data.get('inviteid'):
        return jsonify({'success': False, 'message': 'ID is required'}), 400
    if not data.get('registered'):
        return jsonify({'success': False, 'message': 'Registered status is required'}), 400
    if data.get('registered') == 'True':
        try:
            user = User.query.filter_by(email=data['email']).first()
            db.session.delete(user)
            db.session.commit()
        except:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
    elif data.get('registered') == 'False':
        invite = Invites.query.filter_by(inviteid=data['inviteid']).first()
        db.session.delete(invite)
        db.session.commit()

    return jsonify({'success': True})