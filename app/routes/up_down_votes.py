import datetime
from flask import session, jsonify
from ..models import db, Questions, Plus_ones, Answers, Votes
from flask import Blueprint
from ..utils.role_check import role_required

votes_bpt = Blueprint('votes', __name__)

@votes_bpt.route('/upvote/<int:question_id>', methods=['POST'])
@role_required('user')
def upvote_question(question_id):

    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    # Fetch the question from the database
    # Plus_ones.query.filter_by(questionid=question_id, userid=session.get('user_id')).first()

    plus_one = Plus_ones.query.filter_by(questionid=question_id, userid=session.get('user_id')).first()
    print(plus_one)
    if plus_one:
        db.session.delete(plus_one)
        Questions.query.filter_by(questionid=question_id).first().plus_one -= 1
        db.session.commit()
        new_count = Plus_ones.query.filter_by(questionid=question_id).count()
        return jsonify({"success": True, "new_count": new_count, "status": False})
    plus_one = Plus_ones(questionid=question_id, userid=session.get('user_id'), date=datetime.datetime.now())
    Questions.query.filter_by(questionid=question_id).first().plus_one += 1
    db.session.add(plus_one)
    db.session.commit()
    new_count = Plus_ones.query.filter_by(questionid=question_id).count()

    return jsonify({"success": True, "new_count": new_count, "status": True})

@votes_bpt.route('/upvoteans/<int:answer_id>', methods=['POST'])
@role_required('user')
def upvote_answer(answer_id):
    
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    vote = Votes.query.filter_by(answerid=answer_id, userid=session.get('user_id')).first()
    if vote:
        if vote.vote == 1:
            print('upvote')
            return jsonify({"success": False, "message": "You have already voted"}), 403
        else:

            vote.vote = 1
            Answers.query.filter_by(answerid=answer_id).first().upvotes += 1
            Answers.query.filter_by(answerid=answer_id).first().downvotes -= 1
            db.session.commit()
            upvote=Answers.query.filter_by(answerid=answer_id).first().upvotes
            downvote=Answers.query.filter_by(answerid=answer_id).first().downvotes
            return jsonify({"success": True, "upvote": upvote, "downvote": downvote})
    else :
        print("belwo else")
        question_id=Answers.query.filter_by(answerid=answer_id).first().questionid
        vote = Votes(answerid=answer_id, userid=session.get('user_id'), date=datetime.datetime.now(),questionid=question_id, vote=1)
        Answers.query.filter_by(answerid=answer_id).first().upvotes += 1
        db.session.add(vote)
        db.session.commit()
        upvote=Answers.query.filter_by(answerid=answer_id).first().upvotes
        downvote=Answers.query.filter_by(answerid=answer_id).first().downvotes

        return jsonify({"success": True, "upvote": upvote, "downvote": downvote})



@votes_bpt.route('/downvoteans/<int:answer_id>',methods=['POST'])
@role_required('user')
def downvoteans(answer_id):
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    
    vote = Votes.query.filter_by(answerid=answer_id, userid=session.get('user_id')).first()
    if vote:
        if vote.vote == -1:
            return jsonify({"success": False, "message": "You have already voted"}), 403
        else:
            vote.vote = -1
            Answers.query.filter_by(answerid=answer_id).first().upvotes -= 1
            Answers.query.filter_by(answerid=answer_id).first().downvotes += 1
            db.session.commit()
            upvote=Answers.query.filter_by(answerid=answer_id).first().upvotes
            downvote=Answers.query.filter_by(answerid=answer_id).first().downvotes
            return jsonify({"success": True, "upvote": upvote, "downvote": downvote})
    else :
        question_id=Answers.query.filter_by(answerid=answer_id).first().questionid
        vote = Votes(answerid=answer_id, userid=session.get('user_id'), date=datetime.datetime.now(),questionid=question_id, vote=-1)
        Answers.query.filter_by(answerid=answer_id).first().downvotes += 1
        db.session.add(vote)
        db.session.commit()
        upvote=Answers.query.filter_by(answerid=answer_id).first().upvotes
        downvote=Answers.query.filter_by(answerid=answer_id).first().downvotes

        return jsonify({"success": True, "upvote": upvote, "downvote": downvote})
    
    # question_id=Answers.query.filter_by(answerid=answer_id).first().questionid
    # vote = Votes(answerid=answer_id, userid=session.get('user_id'), date=datetime.datetime.now(),questionid=question_id, vote=-1)
    # Answers.query.filter_by(answerid=answer_id).first().downvotes += 1
    # db.session.add(vote)
    # db.session.commit()
    # new_count = Votes.query.filter_by(answerid=answer_id).count()

    # print('downvote')
    # return jsonify({"message": "Vote updated successfully", "new_count": "50"})
