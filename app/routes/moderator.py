from ..models import db, Questions, Answers, User, Invites
from ..utils.role_check import role_required
from flask import session
from flask import render_template, flash, redirect, url_for
from flask import Blueprint
from sqlalchemy import desc,asc
import humanize
from ..utils.simple_rag import index_qa_pairs

moderator_bpt = Blueprint('moderator', __name__)

@moderator_bpt.route('/dashboard/moderator')
@role_required('moderator')
def moderator_dashboard():
    questions=Questions.query.filter_by(orgid=User.query.filter_by(userid = session.get('user_id')).first().organization).order_by(asc(Questions.date)).all()
    answers=[]
    for question in questions:
        answers.append(Answers.query.filter_by(questionid=question.questionid).all())
    questions_marked_official = [question for question in questions if question.official_answer != ""]
    question_notmarked_official = [question.serializer() for question in questions if question.official_answer == ""]
    # print(question_notmarked_official)

    data_summary={}
    data_summary['users']=len(User.query.filter_by(userid = session.get('user_id')).all())
    data_summary['questions']=len(questions)
    data_summary['answers']=len(answers)
    data_summary['official']=len(questions_marked_official)
    data_summary['unofficial']=len(question_notmarked_official)
    data_summary['total_invites']=len(Invites.query.filter_by(orgid=User.query.filter_by(userid = session.get('user_id')).first().organization).all())

    print(len(questions_marked_official))


    return render_template('ModeratorDashboard.html', questions=questions,data_summary=data_summary,official=questions_marked_official,unofficial=question_notmarked_official,nav="Moderator Dashboard")

@moderator_bpt.route('/question_moderation')
@role_required('moderator')
def question_moderation():
    questions=Questions.query.filter_by(orgid=User.query.filter_by(userid = session.get('user_id')).first().organization).order_by(asc(Questions.date)).all()
    question_notmarked_official = [question.serializer() for question in questions if question.official_answer == ""]
    print(question_notmarked_official)
    return render_template('moderate_questions.html',questions=question_notmarked_official,nav="Moderate Questions")


@moderator_bpt.route('/mark_as_official/<int:answerid>', methods=['get'])
@role_required('moderator')
def mark_as_official(answerid):
    answer = Answers.query.get(answerid)
    answer.marked_as_official = True
    new_question = Questions.query.filter_by(questionid=answer.questionid).first()
    new_question.official_answer = answer.answer

    db.session.commit()
    flash(['Answer marked as official','success'])

    index_qa_pairs(
        {"question": f"{new_question.question_title} {new_question.question_detail}", "answer": new_question.official_answer},
        User.query.filter_by(userid=session.get('user_id')).first().organization,
        Answers.query.filter_by(answerid=answerid).first().questionid
    )
    
    return redirect(url_for('question_and_answer.questions_details', question_id=answer.questionid))


@moderator_bpt.route('/unmark_as_official/<int:answerid>', methods=['get'])
@role_required('moderator')
def unmark_as_official(answerid):
    answer = Answers.query.get(answerid)
    answer.marked_as_official = False
    if len(Answers.query.filter_by(questionid=answer.questionid,marked_as_official=True).all())>=1:
        Questions.query.filter_by(questionid=answer.questionid).first().official_answer = Answers.query.filter_by(questionid=answer.questionid,marked_as_official=True).first().answer
    else:
        Questions.query.filter_by(questionid=answer.questionid).first().official_answer = ""

    db.session.commit()
    flash(['Answer unmarked as official','success'])
    return redirect(url_for('question_and_answer.questions_details', question_id=answer.questionid))