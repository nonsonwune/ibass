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
from ..models.university import University, Course, CourseRequirement, State, ProgrammeType
from ..models.user import User
from ..utils.search import perform_search
from sqlalchemy import or_, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import load_only

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("home.html")


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/search")
def search():
    query_text = request.args.get("q", "").strip()
    state = request.args.get("state")
    types = request.args.getlist("type")

    try:
        # Add caching for search results
        cache_key = f"search_{query_text}_{state}_{'-'.join(sorted(types))}"
        cached_results = cache.get(cache_key)

        if cached_results:
            return cached_results

        # Get available states and types for filters
        available_states = db.session.query(State.name).order_by(State.name).all()
        available_states = [state[0] for state in available_states]

        available_types = db.session.query(ProgrammeType.name)\
            .distinct()\
            .order_by(ProgrammeType.name)\
            .all()
        available_types = [type[0] for type in available_types]

        # Optimize the query with specific columns selection
        universities_query = University.query\
            .join(State, University.state_id == State.id)\
            .join(ProgrammeType, University.programme_type_id == ProgrammeType.id)\
            .options(
                load_only(
                    University.id,
                    University.university_name,
                    University.programme_type_id,
                    University.state_id
                )
            )\
            .filter(
                or_(
                    University.university_name.ilike(f"%{query_text}%"),
                    text("university.search_vector @@ plainto_tsquery('english', :query)")
                    .bindparams(query=query_text),
                )
            )

        # Similar optimization for courses query
        courses_query = Course.query\
            .join(CourseRequirement)\
            .join(University)\
            .options(
                load_only(
                    Course.id,
                    Course.course_name
                )
            )\
            .filter(
                or_(
                    Course.course_name.ilike(f"%{query_text}%"),
                    text("course.search_vector @@ plainto_tsquery('english', :query)")
                    .bindparams(query=query_text),
                )
            )

        # Apply filters
        if state:
            universities_query = universities_query.filter(State.name == state)
            courses_query = courses_query.filter(State.name == state)

        if types:
            universities_query = universities_query.filter(ProgrammeType.name.in_(types))
            courses_query = courses_query.filter(ProgrammeType.name.in_(types))

        # Execute queries
        universities = universities_query.all()
        courses = courses_query.distinct(Course.id).all()

        # Cache the results
        response = render_template(
            "search_results.html",
            query=query_text,
            universities=universities,
            courses=courses,
            universities_count=len(universities),
            courses_count=len(courses),
            states=available_states,
            institution_types=available_types,
            selected_state=state,
            selected_types=types,
            total_results=len(universities) + len(courses),
        )
        
        cache.set(cache_key, response, timeout=300)  # Cache for 5 minutes
        return response

    except Exception as e:
        current_app.logger.error(f"Search error: {str(e)}")
        return jsonify({"error": "Search failed"}), 500


@bp.route("/profile/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user is None:
        flash("User not found.", "danger")
        return redirect(url_for("main.home"))
    return render_template("profile.html", user=user)


@bp.route("/contact", methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    
    # Get general comments (not associated with any university)
    comments = Comment.query.filter_by(
        university_id=None,  # Only get general comments
        parent_id=None  # Only get top-level comments
    ).order_by(Comment.date_posted.desc()).all()
    
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

    return render_template('contact.html', 
                         form=form,
                         comments=comments)


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


@bp.route("/institutions")
def institutions():
    try:
        # Get filter parameters
        state = request.args.get("state")
        types = request.args.getlist("type")
        program_types = request.args.getlist("program")
        sort = request.args.get("sort", "name")  # Default sort by name

        # Base query with joins
        query = University.query\
            .join(State, University.state_id == State.id)\
            .join(ProgrammeType, University.programme_type_id == ProgrammeType.id)\
            .options(
                joinedload(University.state_info),
                joinedload(University.programme_type_info),
                joinedload(University.courses)
            )

        # Apply filters
        if state:
            query = query.filter(State.name == state)
        if types:
            query = query.filter(ProgrammeType.name.in_(types))

        # Apply sorting
        if sort == "name":
            query = query.order_by(University.university_name)
        elif sort == "name_desc":
            query = query.order_by(University.university_name.desc())
        elif sort == "state":
            query = query.order_by(State.name, University.university_name)
        elif sort == "type":
            query = query.order_by(ProgrammeType.name, University.university_name)

        # Get all states and institution types for filters
        states = db.session.query(State.name).order_by(State.name).all()
        institution_types = db.session.query(ProgrammeType.name).distinct().order_by(ProgrammeType.name).all()
        program_type_list = db.session.query(ProgrammeType.category).distinct().order_by(ProgrammeType.category).all()

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 12  # Number of institutions per page
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        institutions = pagination.items

        return render_template(
            "institutions.html",
            institutions=institutions,
            pagination=pagination,
            states=[state[0] for state in states],
            institution_types=[type[0] for type in institution_types],
            program_types=[prog[0] for prog in program_type_list],
            selected_state=state,
            selected_types=types,
            selected_programs=program_types,
            total_institutions=pagination.total
        )

    except Exception as e:
        current_app.logger.error(f"Error in institutions view: {str(e)}")
        flash("An error occurred while loading institutions.", "danger")
        return redirect(url_for("main.home"))
