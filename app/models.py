import html
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
import humanize
import datetime
import re
from . import db
from flask import url_for

class User(db.Model):
    __TableName__ = 'users'
    userid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    firstname = db.Column(db.String(20), nullable=False)
    lastname = db.Column(db.String(20))
    email = db.Column(db.String(50), nullable=False, unique=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    passhash = db.Column(db.String(1024), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    organization = db.Column(db.Integer, db.ForeignKey('organizations.orgid'), nullable=True)
    github_id = db.Column(db.String(200), nullable=True)
     
    def check_password(self, password):
        return check_password_hash(self.passhash, password)
    
    def __repr__(self):
        return f'<User {self.userid}>'
    
    def __str__(self):
        return f'{self.username}'
    
    def serializer(self):
        return {
            'userid': self.userid,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'email': self.email,
            'username': self.username,
            'organization': self.organization,
            'github_id': self.github_id
        }


# NOTE: Store all the questions
class Questions(db.Model):
    __tablename__ = 'Questions'
    questionid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    question_title = db.Column(db.String(50), nullable=False)
    question_detail = db.Column(db.String(200), nullable=False)
    plus_one = db.Column(db.Integer, nullable=False,default=0)
    userid = db.Column(db.Integer, db.ForeignKey('user.userid'), nullable=False)
    official_answer = db.Column(db.Integer, db.ForeignKey('answers.answerid'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    orgid = db.Column(db.Integer, db.ForeignKey('organizations.orgid'), nullable=True)
    ai_answer = db.Column(db.Boolean, nullable=False,default=False)
    tags = db.Column(db.JSON, nullable=False)
    
    def serializer(self):
        return {
            'questionid': self.questionid,
            'question_title': self.question_title,
            'question_detail': self.question_detail,
            'plus_one': self.plus_one,
            'userid': self.userid,
            'email':User.query.filter_by(userid=self.userid).first().username,
            'official_answer': self.official_answer,
            'date': self.date,
            'ai_answer': self.ai_answer,
            'tags': self.tags,
            'no_of_ans': Answers.query.filter_by(questionid=self.questionid).count(),
            'relative_time' : humanize.naturaltime(datetime.datetime.now() - self.date),
            'orgid': self.orgid,
            'status': True if Plus_ones.query.filter_by(userid=self.userid, questionid=self.questionid).first() else False
        }


# NOTE: Plus_ones is a table to store the plus ones for a question
class Plus_ones(db.Model):
    __tablename__ = 'plus_ones'
    plusoneid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    questionid = db.Column(db.Integer, db.ForeignKey('Questions.questionid'), nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey('user.userid'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)


# NOTE: List all answers association with qustions
class Answers(db.Model):
    __tablename__ = 'answers'
    answerid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    answer = db.Column(db.String(2000), nullable=False)
    upvotes = db.Column(db.Integer, nullable=False) # Total Number of down votes
    downvotes = db.Column(db.Integer, nullable=False) # Total Number of upvotes
    questionid = db.Column(db.Integer, db.ForeignKey('Questions.questionid'), nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey('user.userid'), nullable=False)
    marked_as_official = db.Column(db.Boolean, nullable=False, default=False)
    date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Answer {self.answerid}>'
    
    def __str__(self):
        return f'{self.answer}'
    
    def serializer(self):
        formatted_answer = ''
        open_code = True 
        parts = self.answer.split('```')
        try:
            for i, part in enumerate(parts):
                if i == 0:
                    formatted_answer += html.escape(part)  # Add the first part as it is (before the first code block)
                else:
                    if open_code:
                        print(part)
                        parts_lines = part.splitlines()
                        if parts_lines:
                            # Skip the first line and don't add it to the formatted_answer
                            print(parts_lines)
                            # class_name = parts_lines[0].split()[0]
                            
                            part = '\n'.join(parts_lines[1:])  # Remove the first line of the part
                            
                        # Start a new section for the code block
                        formatted_answer += f'''<code class=""><div class="bg-gray-50 p-4 dark:bg-gray-800">{html.escape(part)}'''
                    else:
                        # Close the previous section and append the next part
                        formatted_answer += f"</div></code>{html.escape(part)}"
                    
                    open_code = not open_code  # Toggle the code block state
            
            # Replace bold markdown syntax with HTML <strong> tag
            formatted_answer = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_answer)
            # Replace `text` with <strong>text</strong>
            formatted_answer = re.sub(r'`(.*?)`', r'<strong>\1</strong>', formatted_answer)
            formatted_answer = re.sub(r'^\s*-\s*', '• ', formatted_answer, flags=re.MULTILINE)
        except:
            formatted_answer = self.answer


        return {
            'answerid': self.answerid,
            'answer': self.answer,
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'questionid': self.questionid,
            'userid': self.userid,
            'marked_as_official': self.marked_as_official,
            'date': self.date,
            'username': User.query.filter_by(userid=self.userid).first(),
            'relative_time': humanize.naturaltime(datetime.datetime.now() - self.date),
            'formatted_answer': formatted_answer,
            'votes': self.upvotes - self.downvotes
        }

    

# NOTE: Store upvotes and downvotes for a question
class Votes(db.Model):
    __tablename__ = 'votes'
    voteid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    vote = db.Column(db.Integer, nullable=False)
    questionid = db.Column(db.Integer, db.ForeignKey('Questions.questionid'), nullable=False)
    answerid = db.Column(db.Integer, db.ForeignKey('answers.answerid'), nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey('user.userid'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Vote {self.voteid}>'
    
    def __str__(self):
        return f'{self.vote}'
    
    def serializer(self):
        return {
            'voteid': self.voteid,
            'vote': self.vote,
            'questionid': self.questionid,
            'answerid': self.answerid,
            'userid': self.userid
        }


class Keywords(db.Model):
    __tablename__ = 'keywords'
    keywordid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    keyword = db.Column(db.String(50), nullable=False)
    organization = db.Column(db.Integer, db.ForeignKey('organizations.orgid'), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<Keyword {self.keywordid}>'
    
    def __str__(self):
        return f'{self.keyword}'
    
    def serializer(self):
        return {
            'keywordid': self.keywordid,
            'keyword': self.keyword,
            'organization': self.organization,
            'count': self.count
        }

# class OfficialAnswer(db.Model):
#     __tablename__ = 'officialanswer'
#     officialanswerid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
#     questionid = db.Column(db.Integer, db.ForeignKey('Questions.questionid'))
#     question_text = db.Column(db.Text, nullable=False)
#     answer_text = db.Column(db.Text, nullable=False)
#     embedding = db.Column(db.Text, nullable=False)

#     def __repr__(self):
#         return f'<Official Answer {self.officialanswerid}>'

#     def __str__(self):
#         return f'{self.answer_text}'
    
#     def serializer(self):
#         return {
#             'officialanswerid': self.officialanswerid,
#             'questionid': self.questionid,
#             'question_text': self.question_text,
#             'answer_text': self.answer_text,
#             'embedding': self.embedding
#         }


# NOTE: List down all the organizations with their credentials
class Organizations(db.Model):
    __tablename__ = 'organizations'
    orgid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    orgname = db.Column(db.String(50), nullable=False)
    orgdesc = db.Column(db.String(200), nullable=True)
    orglogo = db.Column(db.LargeBinary, nullable=True)
    orgemail = db.Column(db.String(50), nullable=False)
    orgpassword = db.Column(db.String(1024), nullable=False)
    orgphone = db.Column(db.String(20), nullable=True)
    orgaddress = db.Column(db.String(200), nullable=True)
    orgwebsite = db.Column(db.String(200), nullable=False)
    orgtype = db.Column(db.String(20), nullable=True)
    orgTotalMembers = db.Column(db.Integer, nullable=True,default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)

    def __repr__(self):
        return f'<Organization {self.orgid}>'

    def __str__(self):
        return f'{self.orgname}'
    
    def serializer(self):
        return {
            'orgid': self.orgid,
            'orgname': self.orgname,
            'orgdesc': self.orgdesc,
            'orglogo': self.orglogo,
            'orgemail': self.orgemail,
            'orgphone': self.orgphone,
            'orgaddress': self.orgaddress,
            'orgwebsite': self.orgwebsite,
            'orgtype': self.orgtype,
            'orgTotalMembers': self.orgTotalMembers,
            'orgdate': self.orgdate
        }


# NOTE: Moderators list with their Organization and office location
class Moderators(db.Model):
    __tablename__ = 'moderator'
    modid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    userid = db.Column(db.Integer, db.ForeignKey('user.userid'), nullable=False)
    # subject = db.Column(db.Integer, db.ForeignKey('labels.labelid'), nullable=False)
    orgid = db.Column(db.Integer, db.ForeignKey('organizations.orgid'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    officelocation = db.Column(db.String(200), nullable=False)


    def __repr__(self):
        return f'<Moderator {self.modid}>'

    def __str__(self):
        return f'{self.userid}'
    
    def serializer(self):
        return {
            'modid': self.modid,
            'userid': self.userid,
            'orgid': self.orgid,
            'date': self.date
        }


# NOTE: Labels for questions and their association with moderator
class Labels(db.Model):
    __tablename__ = 'labels'
    labelid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    labelname = db.Column(db.String(50), nullable=False)
    orgid = db.Column(db.Integer, db.ForeignKey('organizations.orgid'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Label {self.labelid}>'

    def __str__(self):
        return f'{self.labelname}'
    
    def serializer(self):
        return {
            'labelid': self.labelid,
            'labelname': self.labelname,
            'labeldesc': self.labeldesc,
            'labeltags': self.labeltags,
            'orgid': self.orgid,
            'date': self.date
        }

    
class ModeratorLabel(db.Model):
    __tablename__ ='moderatorlabel'
    modlabelid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    modid = db.Column(db.Integer, db.ForeignKey('moderator.modid'), nullable=False)
    labelid = db.Column(db.Integer, db.ForeignKey('labels.labelid'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Moderator Label {self.modlabelid}>'
    
class Invites(db.Model):
    __tablename__ = 'invites'
    inviteid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    orgid = db.Column(db.Integer, db.ForeignKey('organizations.orgid'), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    code = db.Column(db.String(50), nullable=False)
    registered = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'<Invite {self.inviteid}>'
    
    def __str__(self):
        return f'{self.email}'
    
    def serializer(self):
        return {
            'inviteid': self.inviteid,
            'orgid': self.orgid,
            'email': self.email,
            'role': self.role,
            'date': self.date,
            'code': self.code,
            'registered': self.registered
        }
    

class Docs(db.Model):
    __tablename__ = 'docs'
    docid = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True)
    docname = db.Column(db.String(50), nullable=False)  # Name of the document
    docdesc = db.Column(db.String(200), nullable=False)  # Description of the document
    docpath = db.Column(db.String(200), nullable=False)  # Path to the file stored on local storage
    orgid = db.Column(db.Integer, db.ForeignKey('organizations.orgid'), nullable=False)

    def __repr__(self):
        return f'<Doc {self.docid}>'

    def serializer(self):
        return {
            'docid': self.docid,
            'docname': self.docname,
            'docdesc': self.docdesc,
            'docpath': url_for('other.serve_uploaded_file', filename=self.docpath),
            'orgid': self.orgid
        }

    # admin=User.query.filter_by(username='admin').first()
    # if not admin:
    #     organization=Organizations(
    #         orgname = "Dummy Organization", orgemail = "org email", orgwebsite = "www.dummy.com",
    #         orgadmin = "", orgtype = "type", orgTotalMembers = 1)
            
    #     admin=User(username='admin', password='admin',
    #                 firstname='admin', lastname='admin',email='admin@admin.com')
    #     # admin_profile=Profile(profileid='1', firstname='admin', lastname='admin',email='admin@admin.com')
    #     db.session.add(organization)
    #     db.session.add(admin)
    #     db.session.commit()

    
