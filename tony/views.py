from flask import render_template, request, jsonify, redirect, url_for
from tony import app, db
from tony.models import Contribution, Comment


@app.route('/')
def index():
    """Home page route."""
    return redirect(url_for('get_contributions'))


@app.route('/contributions', methods=['GET'])
def get_contributions():
    """Get all contributions displayed dynamically with HTMX."""
    # Get all users
    contribs = Contribution.query.all()
    return render_template('contributions.html', contributions=contribs)


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
