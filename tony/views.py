from flask import render_template, request, jsonify, redirect, url_for
from tony import app, db
from tony.models import User, Comment

@app.route('/')
def index():
    """Home page route."""
    return redirect(url_for('discussion'))

@app.route('/users', methods=['GET', 'POST'])
def get_users():
    """Get all users and handle user creation with HTMX."""
    if request.method == 'POST':
        # Handle form submission for creating a new user
        username = request.form.get('username')
        email = request.form.get('email')

        if not username or not email:
            return render_template('users.html', users=User.query.all(), 
                                  error="Username and email are required")

        new_user = User(username=username, email=email)

        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return render_template('users.html', users=User.query.all(), 
                                  error=str(e))

    # Get all users
    users = User.query.all()

    # Check if the request wants HTML or JSON
    if request.headers.get('HX-Request') or request.args.get('format') != 'json':
        return render_template('users.html', users=users)
    else:
        # Return JSON for API clients
        result = [{"id": user.id, "username": user.username, "email": user.email} for user in users]
        return jsonify(result)

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user by ID."""
    user = User.query.get_or_404(user_id)
    return jsonify({"id": user.id, "username": user.username, "email": user.email})


@app.route('/discussion', methods=['GET', 'POST'])
def discussion():
    """Discussion page with comments."""
    if request.method == 'POST':
        # Handle form submission for creating a new comment
        username = request.form.get('username')
        body = request.form.get('body')

        if not username or not body:
            comments = Comment.query.order_by((Comment.upvotes - Comment.downvotes).desc(), Comment.created_at.desc()).all()
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
            comments = Comment.query.order_by((Comment.upvotes - Comment.downvotes).desc(), Comment.created_at.desc()).all()
            if request.headers.get('HX-Request'):
                return render_template('discussion_content.html', comments=comments)
            else:
                return render_template('discussion.html', comments=comments)
        except Exception as e:
            db.session.rollback()
            comments = Comment.query.order_by((Comment.upvotes - Comment.downvotes).desc(), Comment.created_at.desc()).all()
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
