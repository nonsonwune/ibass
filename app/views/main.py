# app/views/main.py

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify,
    current_app,
)
from flask_login import login_required, current_user
from ..models.feedback import Feedback
from ..forms.feedback import ContactForm
from ..extensions import db, cache
from ..models.interaction import Comment
from ..models.university import University, Course
from ..models.user import User
from ..utils.search import perform_search
from sqlalchemy import or_, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("home.html")


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/search")
def search_results():
    query_text = request.args.get("q", "").strip()
    state = request.args.get("state")
    types = request.args.getlist("type")  # Handle multiple type selections

    try:
        # Base universities query
        universities_query = University.query.filter(
            or_(
                University.university_name.ilike(f"%{query_text}%"),
                text(
                    "university.search_vector @@ plainto_tsquery('english', :query)"
                ).bindparams(query=query_text),
            )
        )

        # Base courses query
        courses_query = Course.query.join(
            University, University.university_name == Course.university_name
        ).filter(
            or_(
                Course.course_name.ilike(f"%{query_text}%"),
                Course.abbrv.ilike(f"%{query_text}%"),
                text(
                    "course.search_vector @@ plainto_tsquery('english', :query)"
                ).bindparams(query=query_text),
            )
        )

        # Get all matching results before filtering for filter options
        all_matching_universities = universities_query.all()
        all_matching_courses = courses_query.all()

        # Extract available filter options from results
        available_states = sorted(
            list(set(uni.state for uni in all_matching_universities))
        )
        available_types = sorted(
            list(set(uni.program_type for uni in all_matching_universities))
        )

        # Apply filters if selected
        if state:
            universities_query = universities_query.filter(University.state == state)
            courses_query = courses_query.filter(University.state == state)

        if types:
            universities_query = universities_query.filter(
                University.program_type.in_(types)
            )
            courses_query = courses_query.filter(University.program_type.in_(types))

        # Get final filtered results
        universities = universities_query.all()
        courses = courses_query.all()

        # Count results
        universities_count = len(universities)
        courses_count = len(courses)
        total_results = universities_count + courses_count

        # Handle case where selected filters no longer match any results
        if state and state not in available_states:
            available_states.append(state)
        if types:
            for type_ in types:
                if type_ not in available_types:
                    available_types.append(type_)

        return render_template(
            "search_results.html",
            query=query_text,
            universities=universities,
            courses=courses,
            universities_count=universities_count,
            courses_count=courses_count,
            states=available_states,
            institution_types=available_types,
            selected_state=state,
            selected_types=types,
            selected_levels=[],  # Keeping for backwards compatibility
            program_levels=[],  # Keeping for backwards compatibility
            total_results=total_results,
        )

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in search: {str(e)}")
        flash(
            "An error occurred while performing the search. Please try again.", "danger"
        )
        return redirect(url_for("main.home"))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in search: {str(e)}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for("main.home"))


@bp.route("/profile/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user is None:
        flash("User not found.", "danger")
        return redirect(url_for("main.home"))
    return render_template("profile.html", user=user)


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        feedback = Feedback(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data,
            user_id=current_user.id if current_user.is_authenticated else None,
        )
        try:
            db.session.add(feedback)
            db.session.commit()
            flash("Thank you for your feedback!", "success")
        except:
            db.session.rollback()
            flash(
                "An error occurred while saving your feedback. Please try again.",
                "danger",
            )

        return redirect(url_for("main.contact"))

    # Updated query with joinedload to eagerly load author with score
    comments = (
        Comment.query.options(joinedload(Comment.author))
        .order_by(Comment.date_posted.desc())
        .all()
    )
    return render_template("contact.html", form=form, comments=comments)


@bp.route("/add_comment", methods=["POST"])
@login_required
def add_comment():
    content = request.form.get("comment", "").strip()
    if not content:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("main.contact"))

    new_comment = Comment(content=content, author=current_user)
    try:
        db.session.add(new_comment)
        db.session.commit()
        flash("Your comment has been added.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding comment: {str(e)}")
        flash(
            "An error occurred while adding your comment. Please try again.", "danger"
        )

    return redirect(url_for("main.contact"))


@bp.route("/delete_comment/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user.id == comment.user_id or current_user.is_admin:
        try:
            db.session.delete(comment)
            db.session.commit()
            flash("Comment deleted successfully.", "success")
        except SQLAlchemyError as e:
            db.session.rollback()
            flash("An error occurred while deleting the comment.", "danger")
    else:
        flash("You do not have permission to delete this comment.", "danger")
    return redirect(url_for("main.contact"))
