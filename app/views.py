from flask import render_template, request, jsonify, redirect, url_for
from markupsafe import Markup
from app import app, db
from app.models import Contribution, Comment
from sqlalchemy import or_
import re


def highlight_keywords(text, keywords):
    """
    Highlight keywords in text by wrapping them in span tags with a highlight class.

    Args:
        text (str): The text to search in
        keywords (list): List of keywords to highlight

    Returns:
        Markup: HTML-safe string with highlighted keywords
    """
    if not keywords or not text:
        return Markup(text)

    # Convert text to string if it's not already
    text = str(text)

    # Create a copy of the text for highlighting
    highlighted_text = text

    # Sort keywords by length (longest first) to avoid partial matches
    sorted_keywords = sorted(keywords, key=len, reverse=True)

    for keyword in sorted_keywords:
        # Use regex for case-insensitive matching
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        # Replace with the same text wrapped in a highlight span
        highlighted_text = pattern.sub(lambda m: f'<span class="keyword-highlight">{m.group(0)}</span>', highlighted_text)

    return Markup(highlighted_text)


@app.route('/')
def index():
    """Home page route."""
    return redirect('/contributions')

@app.route('/get-contributions', methods=['GET', 'POST'])
@app.route('/contributions', methods=['GET'])
def get_contributions():
    """
    Unified function to handle both initial page load and dynamic content updates.
    - GET to /contributions: Initial page load
    - POST to /get-contributions: Search with form data
    - GET to /get-contributions: Load more results with pagination
    """
    # Determine if this is a request for the full page or just the content
    is_full_page = request.path == '/contributions'

    # Get search query from appropriate source based on request type
    search_query = request.form.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 30
    offset = (page - 1) * per_page if page > 1 or not search_query else 0

    if search_query:
        # Split the search query into keywords
        keywords = search_query.split()

        # Create a query that searches for contributions containing all keywords
        query = Contribution.query

        for keyword in keywords:
            # Search in all fields
            query = query.filter(
                or_(
                    Contribution.contributor.ilike(f'%{keyword}%'),
                    Contribution.body.ilike(f'%{keyword}%'),
                    # Convert ID to string for searching
                    Contribution.id.cast(db.String).ilike(f'%{keyword}%')
                )
            )

        # Get results with pagination
        contribs = query.order_by(Contribution.id).offset(offset).limit(per_page).all()

        # Create highlighted versions of the contribution fields
        highlighted_contribs = []
        for contrib in contribs:
            # Create a copy of the contribution with highlighted text
            highlighted_contrib = {
                'id': highlight_keywords(contrib.id, keywords),
                'contributor': highlight_keywords(contrib.contributor, keywords),
                'body': highlight_keywords(contrib.body, keywords),
                'time': contrib.time  # No need to highlight the time
            }
            highlighted_contribs.append((contrib, highlighted_contrib))

        # Check if there are more results
        has_more = len(contribs) == per_page and query.count() > offset + per_page
    else:
        # If no search query, return all contributions without highlighting
        contribs = Contribution.query.order_by(Contribution.id).offset(offset).limit(per_page).all()
        highlighted_contribs = [(contrib, None) for contrib in contribs]
        has_more = len(contribs) == per_page and Contribution.query.count() > offset + per_page
        keywords = []

    # Return the appropriate template based on the request type
    if is_full_page:
        return render_template('contributions.html', 
                              contributions=highlighted_contribs, 
                              page=page,
                              has_more=has_more,
                              search_query=search_query,
                              keywords=keywords if search_query else [])
    else:
        return render_template('contributions_content.html', 
                              contributions=highlighted_contribs, 
                              page=page,
                              has_more=has_more,
                              search_query=search_query,
                              keywords=keywords if search_query else [])


@app.route('/discussion', methods=['GET', 'POST'])
def discussion():
    """Discussion page with comments."""
    if request.method == 'POST':
        # Handle form submission for creating a new comment
        username = request.form.get('username')
        body = request.form.get('body')

        if not username or not body:
            comments = Comment.query.order_by((Comment.upvotes - Comment.downvotes).desc(),
                                              Comment.created_at.desc()).all()
            if request.headers.get('HX-Request'):
                return render_template('discussion_content.html', comments=comments,
                                       error="Username and comment are required")
            else:
                return render_template('discussion.html', comments=comments,
                                       error="Username and comment are required")

        new_comment = Comment(username=username, body=body)

        try:
            db.session.add(new_comment)
            db.session.commit()

            # After successful comment creation, return the updated page
            comments = Comment.query.order_by((Comment.upvotes - Comment.downvotes).desc(),
                                              Comment.created_at.desc()).all()
            if request.headers.get('HX-Request'):
                return render_template('discussion_content.html', comments=comments)
            else:
                return render_template('discussion.html', comments=comments)
        except Exception as e:
            db.session.rollback()
            comments = Comment.query.order_by((Comment.upvotes - Comment.downvotes).desc(),
                                              Comment.created_at.desc()).all()
            if request.headers.get('HX-Request'):
                return render_template('discussion_content.html', comments=comments,
                                       error=str(e))
            else:
                return render_template('discussion.html', comments=comments,
                                       error=str(e))

    # Get all comments ordered by vote score (highest first), then by creation date (newest first)
    # We use a hybrid approach with a subquery to order by the calculated vote_score
    comments = Comment.query.order_by((Comment.upvotes - Comment.downvotes).desc(), Comment.created_at.desc()).all()

    # Check if the request wants HTML or JSON
    if request.headers.get('HX-Request'):
        # For HTMX requests, return only the discussion container content
        return render_template('discussion_content.html', comments=comments)
    elif request.args.get('format') != 'json':
        # For regular HTML requests, return the full template
        return render_template('discussion.html', comments=comments)
    else:
        # Return JSON for API clients
        result = [{"id": comment.id, "username": comment.username, "body": comment.body,
                   "created_at": comment.created_at.isoformat(),
                   "upvotes": comment.upvotes, "downvotes": comment.downvotes,
                   "vote_score": comment.vote_score} for comment in comments]
        return jsonify(result)


# Routes for upvoting and downvoting comments
@app.route('/comment/<int:comment_id>/upvote', methods=['POST'])
def upvote_comment(comment_id):
    """Upvote a comment."""
    comment = Comment.query.get_or_404(comment_id)
    comment.upvotes += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

    # Return the updated comment HTML
    return render_template('comment_partial.html', comment=comment)


@app.route('/comment/<int:comment_id>/downvote', methods=['POST'])
def downvote_comment(comment_id):
    """Downvote a comment."""
    comment = Comment.query.get_or_404(comment_id)
    comment.downvotes += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

    # Return the updated comment HTML
    return render_template('comment_partial.html', comment=comment)

# You can add more routes as needed for your application
