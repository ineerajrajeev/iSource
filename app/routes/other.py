import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
from ..models import db, Plus_ones, Organizations,Docs,CustomerSupport,User
from werkzeug.utils import secure_filename
import io
import os
from flask import jsonify
import datetime
from ..utils.role_check import role_required
from ..utils.ai_part import allowed_file
from ..utils.other import generate_demo_data
from ..utils.hybrid_rag import pdf_to_documents
from ..utils.email_notification import notifications
from flask import Blueprint, send_from_directory
from flask import Flask, send_file, abort
import json
import google.generativeai as genai
from ..utils.simple_rag import index_qa_pairs
import random


other_bpt = Blueprint('other', __name__)


@other_bpt.route('/image/<int:id>')
def get_image(id):
    image = Organizations.query.get(id)
    return send_file(io.BytesIO(image.orglogo), mimetype='image/jpeg')


# @app.route('/questiondetail',methods=['GET'])
# def ques():
#     return render_template('QuestionDetails.html') 


@other_bpt.route('/<int:question_id>/plusone', methods=["POST"])
@role_required('user')
def plus_one(question_id):
    if request.method == "POST":
        user_id = int(request.form.get("user_id")) # TODO: Get it from Session ID
        
        plusone_entry = Plus_ones.query.filter_by(questionid=question_id, userid=user_id).first()
        
        if plusone_entry:
            db.session.delete(plusone_entry)
            db.session.commit()
            return jsonify({"message": "Plus one removed successfully", "status": "removed"})
        
        else:
            new_plusone = Plus_ones(
                questionid=question_id,
                userid=user_id,
                date=datetime.datetime.now()
            )
            db.session.add(new_plusone)
            db.session.commit()
            return jsonify({"message": "Plus one added successfully", "status": "added"})
    
    return jsonify({"error": "Invalid request"}), 400
    



# @app.route('/answers/<int:question_id>', methods=['GET', 'POST', 'DELETE', 'PUT'])
# @role_required('user')
# def answers_route(question_id):
    
#         if request.method=='POST':
#             answer=request.form.get('answer')
#             official_answer=request.form.get('official_status')
#             if question_id is None or answer is None:
#                 flash('Please fill the required fields')
#                 return redirect(url_for('questions'))
#             is_toxic, details = is_abusive(answer)
#             if is_toxic:
#                 flash('The answer content is toxic/abusive cannot be posted. We apologize for the inconvenience.', 'error')
#                 return redirect(url_for('questions'))
#             if official_answer == 'no':
#                 answer=Answers(answer=answer,questionid=question_id, userid=session['user_id'],
#                             upvotes=0, downvotes=0, date=datetime.datetime.now())
#                 db.session.add(answer)
#                 db.session.commit()
#                 flash(['Answer added successfully','success'])
#                 return redirect(url_for('questions'))
#             else:
#                 question = Questions.query.filter_by(questionid=question_id).first()
#                 question.official_answer = answer
#                 db.session.commit()
#                 flash(['Official answer added successfully','success'])
#                 return redirect(url_for('questions'))
        
#         # elif request.method=='DELETE': # Delete the answer
#         #     answer_id=request.form.get('answer_id')
#         #     if answer_id is None:
#         #         flash('Please fill the required fields')
#         #         return redirect(url_for('questions'))
#         #     answer=answers.query.filter_by(answerid=answer_id).first()
#         #     db.session.delete(answer)
#         #     db.session.commit()
#         #     flash(['Answer deleted successfully','success'])
#         #     return redirect(url_for('questions'))
        
#         elif request.method=='PUT': # Vote the answer
#             answer_id=request.form.get('answer_id')
#             vote = request.form.get('vote') # +1 for upvote and -1 for downvote, +10 for official answer
#             answer=Answers.query.filter_by(answerid=answer_id).first()

#             if vote == 1:
#                 answer.upvotes+=1

#             elif vote == 10:
#                 answer.marked_as_official=True
#                 question = questions.query.filter_by(questionid=answer.questionid).first()
#                 question.official_answer = answer.answer

#             elif vote == -1:
#                 answer.downvotes+=1

#             db.session.commit()
#             flash(['Voted successfully','success'])
#             return redirect(url_for('questions'))


# Configure upload folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'upload')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}


# Utility function to validate file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route to view file in the browser
@other_bpt.route('/view/<filename>')
def view_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=False)
    flash('File not found', 'danger')
    return redirect(url_for('user.login'))


# Route to serve uploaded files
@other_bpt.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# Route to handle file upload
@other_bpt.route('/upload', methods=['POST'])
def upload_file():
    # Retrieve form data
    docdesc = request.form.get('docdesc', '')  # Default to an empty string if not provided
    orgid = session.get('org_id')

    # Check if a file was submitted
    if 'file' not in request.files:
        flash('No file part in the form', 'danger')
        return redirect(request.url)

    file = request.files['file']

    # Check for empty file submission
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(request.url)

    # Validate and process the file
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        try:
            # Ensure the upload folder exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Save file to the upload folder
            file.save(file_path)
        except Exception as e:
            flash(f"Failed to save the file: {e}", 'danger')
            return redirect(url_for('user.login'))

        # Save file details to the database
        new_doc = Docs(
            docname=file.filename,
            docdesc=docdesc,
            docpath=file_path,
            orgid=orgid
        )
        try:
            db.session.add(new_doc)
            db.session.commit()
            flash(['File successfully uploaded and details saved!', 'success'])

            # Process the uploaded PDF file
            pdf_to_documents(file_path, orgid)
            return redirect(url_for('user.login'))
        except Exception as e:
            flash(f"Failed to save file details to database: {e}", 'danger')
            db.session.rollback()
            return redirect(url_for('user.login'))
    else:
        flash('Invalid file format. Only PDF files are allowed.', 'danger')
        return redirect(url_for('user.login'))


@other_bpt.route('/dashboard/admin')
def admin_dashboard():
    data = generate_demo_data()
    return render_template('admin_dashboard.html', data=data)


@other_bpt.route('/logout')
def logout():
    session.pop('user_id',None)
    session.pop('org_id',None)
    return redirect(url_for('user.login'))

@other_bpt.route("/trigger/<string:redirect_url>/<string:message_title>/<string:message_body>")
def trigger_notification(redirect_url, message_title, message_body):
    # Flash the message with the provided title and body
    flash(['Background process completed!', 'success', message_title, message_body])
    try:
        # Redirect to the specified route
        return redirect(url_for(redirect_url))
    except Exception as e:
        # Handle invalid redirect URL gracefully
        return f"Error: {e}", 400

# @app.route('/check_notification/<int:question_id>', methods=['GET'])
# def check_notification(question_id):
#     print("Checking notification for question ID:", question_id)
#     if question_id in notification_data:
#         # Return the notification data and remove it after sending
#         return jsonify(notification_data.pop(question_id))
#     return jsonify({"status": "pending"})

@other_bpt.route('/check_notifications')
def check_notifications():
    if notifications:
        # Pop the first notification from the list
        notification = notifications.pop(0)
        return jsonify({"notifications": [notification]})
    else:
        # If there are no notifications, return an empty list
        return jsonify({"notifications": []})
    
@other_bpt.route('/chat')
@role_required(['moderator','organization'])
def chat():
    # backend={'feedback': 'nothing new', 'messageId': 'msg_1738526396414_84nsy8dre', 'message': 'Chatbot Query\nthis', 'conversation': [{'sender': 'You', 'message': 'hi', 'messageId': 'msg_1738526351890_jjd28h9jw', 'timestamp': '01:29 AM'}, {'sender': 'Bot', 'message': 'Hello! How can I help you today?', 'messageId': 'msg_1738526355834_5gd181q2e', 'timestamp': '01:29 AM'}, {'sender': 'You', 'message': 'on', 'messageId': 'msg_1738526385624_gxmfhamj7', 'timestamp': '01:29 AM'}, {'sender': 'Bot', 'message': 'This context does not mention anything about chatbots. So I cannot answer this question from the provided context.', 'messageId': 'msg_1738526389457_tkizdkbuy', 'timestamp': '01:29 AM'}, {'sender': 'You', 'message': 'this', 'messageId': 'msg_1738526392438_c8uqj30jc', 'timestamp': '01:29 AM'}, {'sender': 'Bot', 'message': 'Chatbot Query\nthis', 'messageId': 'msg_1738526396414_84nsy8dre', 'timestamp': '01:29 AM'}]}
    users = [
    {"id": "1", "name": "User 1", "is_active": True},
    {"id": "2", "name": "User 2", "is_active": False},
    {"id": "3", "name": "User 3", "is_active": False},
    {"id": "4", "name": "User 4", "is_active": True},
    ]
    messages = {}
    requests=CustomerSupport.query.filter_by(solution="pending").all()
    for request in requests:
        messages[str(request.supportid)]=request.conversation_json
    # print(messages)

    users=[]
    for request in requests:
        users.append({"id":str(request.supportid),"name":User.query.filter_by(userid=request.userid).first().firstname+" "+User.query.filter_by(userid=request.userid).first().lastname,"is_active":True})
    # print(users)


    return render_template('chat.html',nav="Chat Feedback",users=users, messages=messages, messages_json=json.dumps(messages), users_json=json.dumps(users))


@other_bpt.route('/chatorg')
@role_required(['organization'])
def chatorg():
    # backend={'feedback': 'nothing new', 'messageId': 'msg_1738526396414_84nsy8dre', 'message': 'Chatbot Query\nthis', 'conversation': [{'sender': 'You', 'message': 'hi', 'messageId': 'msg_1738526351890_jjd28h9jw', 'timestamp': '01:29 AM'}, {'sender': 'Bot', 'message': 'Hello! How can I help you today?', 'messageId': 'msg_1738526355834_5gd181q2e', 'timestamp': '01:29 AM'}, {'sender': 'You', 'message': 'on', 'messageId': 'msg_1738526385624_gxmfhamj7', 'timestamp': '01:29 AM'}, {'sender': 'Bot', 'message': 'This context does not mention anything about chatbots. So I cannot answer this question from the provided context.', 'messageId': 'msg_1738526389457_tkizdkbuy', 'timestamp': '01:29 AM'}, {'sender': 'You', 'message': 'this', 'messageId': 'msg_1738526392438_c8uqj30jc', 'timestamp': '01:29 AM'}, {'sender': 'Bot', 'message': 'Chatbot Query\nthis', 'messageId': 'msg_1738526396414_84nsy8dre', 'timestamp': '01:29 AM'}]}
    
    messages = {}
    requests=CustomerSupport.query.filter_by(solution="uplift").all()
    for request in requests:
        messages[str(request.supportid)]=request.conversation_json
    # print(messages)

    users=[]
    for request in requests:
        users.append({"id":str(request.supportid),"name":User.query.filter_by(userid=request.userid).first().firstname+" "+User.query.filter_by(userid=request.userid).first().lastname,"is_active":True})
    # print(users)


    return render_template('chatorg.html',nav="Chat Feedback",users=users, messages=messages, messages_json=json.dumps(messages), users_json=json.dumps(users))


genai.configure(api_key="AIzaSyAb4TTvJNOcSeZe4BgwvUrBgUQeAoYvNXI")


def geminiGenerate(prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text


@other_bpt.route('/api/moderatorresponse', methods=['POST'])
def moderatorresponse():
    data = request.get_json()
    print(data['moderatorResponse'])
    customer_chat = CustomerSupport.query.filter_by(supportid=data["customersupportid"]).first()
    summarize = geminiGenerate(str(customer_chat.conversation_json) + " Summarize this chat")
    customer_chat.solution=data["moderatorResponse"]
    org_id = User.query.filter_by(userid=session.get('user_id')).first()
    if data["moderatorResponse"] not in ["pending","uplift"]:
        print("working")
        index_qa_pairs({
            "question": summarize,
            "answer": data["moderatorResponse"]
        }, session.get('org_id') if not org_id else org_id.organization, random.randint(1, 10000))
    db.session.commit()
    return jsonify({"status": "success"}), 200