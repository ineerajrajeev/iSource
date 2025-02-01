import datetime
import random
from datetime import timedelta
from ..models import User, Questions, Answers, Keywords
from sqlalchemy import func
from collections import defaultdict
from flask import session

def generate_demo_data():
    # Generate sample time-series data for the past 10 days
    dates = [(datetime.datetime.now() - datetime.timedelta(days=x)).strftime('%Y-%m-%d') for x in range(10)]

    # Trending tags: Fetch the top 5 keywords ordered by their count
    trending_tags = [
        {'name': tag.keyword, 'count': tag.count}
        for tag in Keywords.query.filter_by(organization=session.get('org_id')).order_by(Keywords.count.desc()).limit(5).all()
    ]

    # Time-series data: Initialize dictionaries for questions and answers
    questions_per_day = defaultdict(int)
    answers_per_day = defaultdict(int)

    # Count questions per day using GROUP BY
    question_counts = (
        Questions.query.filter_by(orgid=session.get('org_id')).with_entities(func.date(Questions.date).label('q_date'), func.count(Questions.questionid))
        .group_by(func.date(Questions.date))
        .all()
    )
    for q_date, count in question_counts:
        questions_per_day[q_date] = count

    # Count answers per day using GROUP BY
    
    # Subquery to fetch question IDs for the specific orgid
    question_ids_subquery = Questions.query.filter_by(orgid=session.get('org_id')).with_entities(Questions.questionid).subquery()

    # Main query to count answers grouped by date where question IDs match
    answer_counts = (
        Answers.query
        .filter(Answers.questionid.in_(question_ids_subquery))  # Filter answers matching question IDs
        .with_entities(
            func.date(Answers.date).label('a_date'),  # Extract date
            func.count(Answers.answerid).label('answer_count')  # Count answers
        )
        .group_by(func.date(Answers.date))  # Group by date
        .all()
    )   
    print(answer_counts)
    for a_date, count in answer_counts:
        answers_per_day[a_date] = count

    # Top 5 questions: Ordered by the most recent date
    top_questions = [
        {
            'question': question.question_title,
            'views': getattr(question, 'views', 0),  # Default to 0 if 'views' does not exist
            'answers': Answers.query.filter_by(questionid=question.questionid).count(),
        }
        for question in Questions.query.order_by(Questions.date.desc()).limit(5).all()
    ]

    # Final data structure
    return {
        "trending_tags": trending_tags,
        'time_series_data': {
            'dates': dates,
            'questions': [questions_per_day[date] for date in dates],
            'answers': [answers_per_day[date] for date in dates],
        },
        'top_questions': top_questions,
    }