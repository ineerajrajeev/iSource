import datetime
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from ..models import db, User, Questions, Plus_ones, Answers, Votes, Keywords,Organizations,CustomerSupport
import random
from langchain_community.llms.ollama import Ollama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import humanize
import random
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import threading
import random
from ..utils.role_check import role_required
from ..utils.ai_part import lemmatize_text, is_abusive, keybertmodel
from ..utils.email_notification import notifications
from flask import Blueprint
from concurrent.futures import ThreadPoolExecutor
from ..utils.hybrid_rag import hybrid_search
from ..utils.simple_rag import search_answer
from flask import current_app
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
import os


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Gemini LLM initialization
gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-pro",            # or 'gemini-1.5-flash' etc.
    google_api_key=GOOGLE_API_KEY
)

# Prompt template to incorporate context + user question
rag_prompt = PromptTemplate.from_template(
    """You are a helpful and accurate AI assistant. 
Use the following context to answer the user's question accurately and succinctly.

Context:
{context}

Question:
{question}
"""
)

# Create the chain
gemini_chain = LLMChain(
    llm=gemini_llm,
    prompt=rag_prompt,
    verbose=True
)

QA_bpt = Blueprint('question_and_answer', __name__)
executor = ThreadPoolExecutor(max_workers=5)

api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=200)
wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)

@QA_bpt.route('/questions', methods=['GET', 'POST', 'DELETE', 'PUT'])
def questions():

    filter=request.args.get('filter','date')

    if request.method=='POST': # Add the question
        question=request.form.get('question')
        question=questions(question=question,userid=session['user_id'].first(), plus_one=0, official_answer="")
        db.session.add(question)
        db.session.commit()
        flash(['Question added successfully','success'])
        return redirect(url_for('question_and_answer.questions'))
    

    elif request.method=='DELETE': # Delete the question
        question_id=request.form.get('question_id')
        if question_id is None:
            flash('Please fill the required fields')
            return redirect(url_for('question_and_answer.questions'))
        question=questions.query.filter_by(questionid=question_id).first()
        db.session.delete(question)
        db.session.commit()
        flash(['Question deleted successfully','success'])
        return redirect(url_for('question_and_answer.questions'))
    

    # elif request.method=='PUT': # Plus one the question
    #     # Plus one
    #     question_id=request.form.get('question_id')
    #     # If already plus one remove plus one
    #     if plus_ones.query.get(question_id = int(question_id), userid = int(session['user_id'])):
    #         plus_ones.query.filter_by(question_id = int(question_id), userid = int(session['user_id'])).delete()
    #         questions.query.filter_by(questionid=question_id).first().plus_one-=1
    #         db.session.commit()
            
    

    else: # Get all questions
        question_whole=[]
        if session.get('org_id'):
            if filter=="date":
                print("date")
                questions = Questions.query.filter_by(orgid=session.get('org_id')).order_by(Questions.date.desc()).all()
            elif filter=="plus_one":
                print("plus_one")
                questions = Questions.query.filter_by(orgid=session.get('org_id')).order_by(Questions.plus_one.desc()).all()
            elif filter=="plus_one_date":
                questions = Questions.query.filter_by(orgid=session.get('org_id')).order_by(Questions.date.desc(), Questions.plus_one.asc()).all()
            else:
                questions = Questions.query.filter_by(orgid=session.get('org_id')).all()

            for question in questions:
                question_whole.append(question.serializer())
            
            if User.query.filter_by(userid=session.get('user_id')).first():
                role=User.query.filter_by(userid=session.get('user_id')).first().role
            elif Organizations.query.filter_by(orgid=session.get('org_id')).first():
                role='organization'
            else:
                role="user"
            return render_template('questions.html',questions=question_whole,nav="All Questions",role=role,filter=filter)
        else:
            if filter=="date":
                print("date")
                questions = Questions.query.filter_by(orgid=User.query.filter_by(userid=session.get('user_id')).first().organization).order_by(Questions.date.desc()).all()
            elif filter=="plus_one":
                print("plus_one")
                questions = Questions.query.filter_by(orgid=User.query.filter_by(userid=session.get('user_id')).first().organization).order_by(Questions.plus_one.desc()).all()
            elif filter=="plus_one_date":
                questions = Questions.query.filter_by(orgid=User.query.filter_by(userid=session.get('user_id')).first().organization).order_by(Questions.date.desc(), Questions.plus_one.asc()).all()
            else:
                questions = Questions.query.filter_by(orgid=User.query.filter_by(userid=session.get('user_id')).first().organization).all()

            for question in questions:
                question_whole.append(question.serializer())
            
            if User.query.filter_by(userid=session.get('user_id')).first():
                role=User.query.filter_by(userid=session.get('user_id')).first().role
            elif Organizations.query.filter_by(orgid=session.get('org_id')).first():
                role='organization'
            else:
                role="user"
            return render_template('questions.html',questions=question_whole,nav="All Questions",role=role,filter=filter)
    
    
@QA_bpt.route('/answer_delete/<int:answerid>', methods=['GET'])
@role_required(['admin', 'moderator'])
def answer_delete(answerid):
    answer = Answers.query.get(answerid)
    official_ans=answer.answer
    question_id = answer.questionid
    db.session.delete(answer)
    db.session.commit()

    if Questions.query.filter_by(questionid=question_id).first().official_answer == official_ans:
        if len(Answers.query.filter_by(questionid=question_id,marked_as_official=True).all())>=1:
            Questions.query.filter_by(questionid=question_id).first().official_answer = Answers.query.filter_by(questionid=question_id,marked_as_official=True).order_by(Answers.date.desc()).first().answer
        else:
            Questions.query.filter_by(questionid=question_id).first().official_answer = ""

    db.session.commit()

    flash(['Answer deleted successfully','success'])
    return redirect(url_for('question_and_answer.questions_details', question_id=question_id))


@QA_bpt.route('/questions_details/<int:question_id>', methods=['GET', 'POST'])
@role_required(['user', 'moderator'])
def questions_details(question_id):

    if request.method=='POST':
        answer=request.form.get('answer')
        if User.query.get(session['user_id']).role=='moderator':
            isAnsOfficial = True if request.form.get('official_status') == "yes" else False
        else:
            isAnsOfficial = False
        
        if answer is None:
            flash('Please fill the required fields')
            return redirect(url_for('question_and_answer.questions'))
        
        newAnswer=Answers(answer=answer, questionid=question_id, userid=session['user_id'],
                       upvotes=0, downvotes=0, marked_as_official=isAnsOfficial, date=datetime.datetime.now())
        db.session.add(newAnswer)
        db.session.commit()

        if isAnsOfficial:
            question = Questions.query.filter_by(questionid=question_id).first()
            question.official_answer = answer
            db.session.commit()


            # Generate BERT embedding for the question text
            # inputs = tokenizer(question_text, return_tensors='pt', truncation=True, padding=True)
            # with torch.no_grad():
            #     outputs = model(**inputs)
            #     embedding = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()

            # # Create the official answer entry
            # official_entry = OfficialAnswer(
            #     questionid=question_id,
            #     embedding=str(embedding),
            #     question_text=question_text,
            #     answer_text=answer
            # )
            # db.session.add(official_entry)
            # db.session.commit()


        flash(['Answer added successfully','success','Answer Provided'])
        return redirect(url_for('question_and_answer.questions_details', question_id=question_id))
            

    else: # Get all questions
        questions=Questions.query.filter_by(questionid=question_id).first()
        
        timestamp = questions.date

        # Get the current time
        now = datetime.datetime.now()

        # Calculate the relative time
        relative_time = humanize.naturaltime(now - timestamp)
        user_question=User.query.filter_by(userid=questions.userid).first()

        answer_all = Answers.query.filter_by(questionid=question_id).order_by(Answers.date.desc()).all()

        answers_list=[]
        for answer in answer_all:
            answers_list.append(answer.serializer())

        return render_template('QuestionDetails.html',question=questions.serializer(),relative_time=relative_time,user_question=user_question,answers=answers_list,nav="Question {}".format(question_id),role=User.query.filter_by(userid=session['user_id']).first().role)


@QA_bpt.route('/questions_delete/<int:question_id>',methods=['GET'])
@role_required(['user','moderator','organization'])
def questions_delete(question_id):
    user=User.query.filter_by(userid=session['user_id']).first()
    question=Questions.query.filter_by(questionid=question_id).first()
    if question.userid!=user.userid and user.role!='moderator' and user.role!='organization':
        flash('You are not authorized to delete this question')
        return redirect(url_for('user.myquestions'))
    answers=Answers.query.filter_by(questionid=question_id).all()
    plus_ones=Plus_ones.query.filter_by(questionid=question_id).all()
    votes=Votes.query.filter_by(questionid=question_id).all()
    for answer in answers:
        db.session.delete(answer)
    for plus_one in plus_ones:
        db.session.delete(plus_one)
    for vote in votes:
        db.session.delete(vote)
    db.session.delete(question)
    db.session.commit()
    flash(['Question deleted successfully','success'])
    if user.role=='moderator' or user.role=='organization':
        return redirect(url_for('moderator.moderator_dashboard'))
    return redirect(url_for('user.myquestions'))


@QA_bpt.route('/ask_question', methods=["GET", "POST"])
@role_required('user')
def ask_question():
    if request.method == "POST":
        title = request.form.get('title')
        body = request.form.get('body')
        tags = request.form.get('tags')
        random_id = random.randint(1000, 9999)

        is_toxic, details = is_abusive(title + ' ' + body + ' ' + tags)

        if is_toxic:
            flash('The question content is toxic/abusive cannot be posted. We apologize for the inconvenience.', 'error')
            return redirect(url_for('question_and_answer.ask_question'))

        # Basic validation
        if not title or not body or not tags:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('question_and_answer.ask_question'))
        
        # Get organization ID
        org_id = User.query.filter_by(userid=session.get('user_id')).first().organization

        # Process tags
        tag_objects = [tag.strip() for tag in tags.split(',')]

        # Save the question in the database
        new_question = Questions(
            questionid=random_id,
            question_title=title,
            question_detail=body,
            date=datetime.datetime.now(),
            official_answer="",
            userid=session.get('user_id'),
            tags=tag_objects,
            orgid=org_id
        )

        db.session.add(new_question)
        db.session.commit()

        app = current_app._get_current_object()
        executor.submit(ask_question_function, app, random_id, org_id, title, body, tag_objects)

        flash(['Your question is being posted in the background!', 'success'])
        return redirect(url_for('question_and_answer.questions'))

    return render_template('AskQuestion.html', nav="Ask Question", role=User.query.filter_by(userid=session['user_id']).first().role)


def ask_question_function(app, question_id, org_id, title, body, tags):
    """
    Integrates Gemini (via LangChain) into the ask_question_function 
    to produce AI-generated answers based on hybrid RAG context.
    """
    try:
        with app.app_context():
            # 1) Perform hybrid and simple RAG search
            hybrid_context = hybrid_search(f"{title} {body}", org_id, score_threshold=0.5)
            simple_context = search_answer(f"{title} {body}", org_id)
            print(hybrid_context)
            print(simple_context)

            # 2) If no context is found, fetch additional information from Wikipedia
            wiki_context = ""
            if not hybrid_context and not simple_context:
                wiki_context = wiki_tool.run(title + " " + body)

            # 3) Build a combined context
            combined_context = ""

            if hybrid_context and simple_context:
                combined_context += f"Hybrid Search:\n{hybrid_context}\n\nQA Pair Context:\n{simple_context}\n"
            elif simple_context:
                combined_context += f"QA Pair Context:\n{simple_context}\n"
            elif hybrid_context:
                combined_context += f"Hybrid Search:\n{hybrid_context}\n"
            elif wiki_context:
                combined_context += f"Wikipedia Context:\n{wiki_context}\n"

            if not combined_context:
                combined_context = "No relevant context found. Use best available knowledge."

            print(combined_context)
            
            # 4) Run the chain with Gemini
            response = gemini_chain.run(
                context=combined_context,
                question=f"{title}\n{body}"
            )
            print(response)

            # 5) Check toxicity
            is_toxic, details = is_abusive(response)
            if is_toxic:
                print("AI response flagged as toxic:", details)
                # Return None or empty string if toxic. We'll do None:
                return None

            # 6) Save AI-generated response to DB
            extracted_keywords = [keyword[0] for keyword in keybertmodel.extract_keywords(response)] + tags
            new_answer = Answers(
                answer=response,
                questionid=question_id,
                userid=1,  # or the relevant user ID
                upvotes=0,
                downvotes=0,
                marked_as_official=False,
                date=datetime.datetime.now(),
            )
            db.session.add(new_answer)

            # Update question status
            question = Questions.query.filter_by(questionid=question_id).first()
            if question:
                question.ai_answer = True

            # Upsert keywords
            for key in extracted_keywords:
                key_lower = lemmatize_text(key.lower())
                keyword_record = Keywords.query.filter_by(keyword=key_lower).first()
                if keyword_record:
                    keyword_record.count += 1
                else:
                    db.session.add(Keywords(keyword=key_lower, organization=org_id, count=1))

            db.session.commit()
            print("Gemini successfully answered and saved the response.")

            # IMPORTANT: Return the response so the caller (chatbot) can use it
            return response

    except Exception as e:
        print("Error in ask_question_function:", str(e))
        return None  # Return None if something breaks


@QA_bpt.route('/api/chatbot', methods=['POST'])
def chatbot():
    """
    Chatbot endpoint that reuses ask_question_function logic.
    """
    try:
        data = request.get_json()
        conversation = data.get('conversation', [])
        print(data)
        
        if not conversation:
            return jsonify({"error": "No conversation provided"}), 400

        # Extract the LAST user message
        user_message = ""
        for msg in reversed(conversation):
            if msg.get('sender') == 'You':
                user_message = msg.get('message', '').strip()
                break

        if not user_message:
            return jsonify({"error": "No user message found"}), 400

        # Example placeholders
        question_id = 9999
        org_id = 1
        tags = ["chatbot"]  # Example tag

        # Call ask_question_function, using the user message as 'body'
        ai_response = ask_question_function(
            app=current_app,
            question_id=question_id,
            org_id=org_id,
            title="Chatbot Query",
            body=user_message,
            tags=tags
        )

        if ai_response is None:
            # Could mean toxicity or an error occurred
            return jsonify({"reply": "Sorry, I cannot answer that."}), 200

        return jsonify({"reply": ai_response}), 200

    except Exception as e:
        print(f"Error in chatbot API: {e}")
        return jsonify({"error": "An error occurred while processing the message"}), 500

@QA_bpt.route('/api/feedback', methods=['POST'])
def feedback():
    print(session.get('user_id'))
    if session.get('user_id')==None:
        return jsonify({"error": "User not logged in"}), 400

    """
    Feedback endpoint for chatbot responses.
    """
    try:
        data = request.get_json()
        print(data)
        list=[]
        messages={}
        for i in data['conversation']:
            if i['messageId']==data['messageId']:
                i['feedback']=data['feedback']
            list.append(i)
        user=session.get('user_id')
        customersupport=CustomerSupport(userid=user,conversation_json=list,date=datetime.datetime.now(),solution="pending")
        db.session.add(customersupport)
        db.session.commit()
        messages[user]=list
        conversation = data.get('conversation')
        feedback = data.get('feedback')

        

        print(messages)

        if not conversation or not feedback:
            return jsonify({"error": "Missing response or feedback"}), 400

        # Process the feedback (e.g., update the model, etc.)
        # print(f"Feedback received for response: {conversation}, feedback: {feedback}")

        return jsonify({"message": "Feedback received successfully"}), 200

    except Exception as e:
        print(f"Error in feedback API: {e}")
        return jsonify({"error": "An error occurred while processing the feedback"}), 500


# @QA_bpt.route('/api/demo')
# def demo():
#     customers=CustomerSupport.query.all()

#     customers[0]
#     for customer in customers:
#         for question in customer.conversation_json:
#             # print(question)
#             try:
#                 if question['feedback']:
#                     print('message:'+ question['message'])
#                     print('feedback: '+question['feedback'])
#             except:
#                 continue
#     return jsonify({"message": "Feedback received successfully"}), 200

# @QA_bpt.route('/api/demo')
# def demo():
#     customers=CustomerSupport.query.all()

#     customers[0]
#     for customer in customers:
#         question=customer.conversation_json
#         print('user message:'+ question[3-1]['message'])
#         print('chatbot response: '+question[3]['message'])
#         print('feedback: '+question[3]['feedback'])
#         # for i in range(0,len(customer.conversation_json)):
#         #     # print(question)
#         #     try:
#         #         if question[i]['feedback']:
#         #             print('user message:'+ question[i-1]['message'])
#         #             print('chatbot response: '+question[i]['message'])
#         #             print('feedback: '+question[i]['feedback'])
#         #     except:
#         #         continue
#     return jsonify({"message": "Feedback received successfully"}), 200


# index_qa_pairs(
#         {"question": f"{new_question.question_title} {new_question.question_detail}", "answer": new_question.official_answer},
#         User.query.filter_by(userid=session.get('user_id')).first().organization,
#         Answers.query.filter_by(answerid=answerid).first().questionid
#     )

@QA_bpt.route('/api/demo')
def demo():
    customers=CustomerSupport.query.all()

    customers[0]
    for customer in customers:
        question=customer.conversation_json
        for i in range(0,len(customer.conversation_json)):
            try:
                if question[i]['feedback']:
                    print('user message:'+ question[i-1]['message'])
                    print('chatbot response: '+question[i]['message'])
                    print('feedback: '+question[i]['feedback'])
        
            except:
                continue
    return jsonify({"message": "Feedback received successfully"}), 200