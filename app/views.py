import json
import re
import os
from pathlib import Path

from flask import render_template, request, jsonify, redirect, send_from_directory, url_for, flash
from markupsafe import Markup
from mistralai import Mistral
from sqlalchemy import or_

from app import app, db
from app.models import Contribution, Comment, Answer, SearchLog, AnalyseChat, DownloadLog
from app.utils import generate_confirmation_token, send_confirmation_email


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
        highlighted_text = pattern.sub(lambda m: f'<span class="keyword-highlight">{m.group(0)}</span>',
                                       highlighted_text)

    return Markup(highlighted_text)


@app.route('/')
def index():
    """Home page route."""
    return redirect('/contributions')


def get_contributions_data(search_query='', page=1):
    """
    Helper function to fetch and process contributions data.
    Used by both the contributions and get-contributions routes.

    Args:
        search_query (str): The search query to filter contributions
        page (int): The page number for pagination

    Returns:
        tuple: (highlighted_contribs, page, has_more, search_query, keywords, total_count)
    """
    per_page = 30
    offset = (page - 1) * per_page if page > 1 or not search_query else 0

    # Create a query that searches for contributions containing all keywords
    query = Contribution.query

    if search_query:
        # Split the search query into keywords
        keywords = search_query.split()

        for keyword in keywords:
            search_fields = [
                Contribution.formatted_time.ilike(f'%{keyword}%'),
                Contribution.body.ilike(f'%{keyword}%'),
                # Convert ID to string for searching
                Contribution.id.cast(db.String).ilike(f'%{keyword}%'),
                Contribution.anonymized_contributor.ilike(f'%{keyword}%')
            ]

            query = query.filter(or_(*search_fields))

        # Get the total count of matching contributions
        total_count = query.count()

        # Get results with pagination
        contribs = query.order_by(Contribution.id).offset(offset).limit(per_page).all()

        # Create highlighted versions of the contribution fields
        highlighted_contribs = []
        for contrib in contribs:
            highlighted_contribs.append({
                'id': highlight_keywords(contrib.id, keywords),
                'anonymized_contributor': highlight_keywords(contrib.anonymized_contributor, keywords),
                'body': highlight_keywords(contrib.body, keywords),
                'formatted_time': highlight_keywords(contrib.formatted_time, keywords)
            })

        # Check if there are more results
        has_more = len(contribs) == per_page and total_count > offset + per_page
    else:
        # If no search query, return all contributions without highlighting
        total_count = query.count()
        highlighted_contribs = query.order_by(Contribution.id).offset(offset).limit(per_page).all()
        has_more = len(highlighted_contribs) == per_page and total_count > offset + per_page
        keywords = []

    return highlighted_contribs, page, has_more, search_query, keywords if search_query else [], total_count


@app.route('/contributions', methods=['GET'])
def contributions():
    """
    Route for the initial page load of contributions.
    - GET to /contributions: Initial page load with full HTML template
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')

    highlighted_contribs, page, has_more, search_query, keywords, total_count = get_contributions_data(search_query,
                                                                                                       page)

    return render_template('contributions.html',
                           contributions=highlighted_contribs,
                           page=page,
                           has_more=has_more,
                           search_query=search_query,
                           keywords=keywords,
                           total_count=total_count)


@app.route('/get-contributions', methods=['GET', 'POST'])
def get_contributions():
    """
    Route for dynamic content updates.
    - POST to /get-contributions: Search with form data
    - GET to /get-contributions: Load more results with pagination
    """
    # Get search query from appropriate source based on request type
    search_query = request.form.get('search', request.args.get('search', ''))
    page = request.args.get('page', 1, type=int)

    # Log search queries when using POST method with a search query
    if request.method == 'POST' and search_query:
        # Get the requester's IP address
        ip_address = request.remote_addr
        # Get the user agent
        user_agent = request.headers.get('User-Agent', '')

        # Create a new search log entry
        search_log = SearchLog(
            search_content=search_query,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Save the log to the database
        try:
            db.session.add(search_log)
            db.session.commit()
        except Exception as e:
            # Log the error but continue with the request
            print(f"Error logging search query: {str(e)}")
            db.session.rollback()

    highlighted_contribs, page, has_more, search_query, keywords, total_count = get_contributions_data(search_query,
                                                                                                       page)

    return render_template('contributions_content.html',
                           contributions=highlighted_contribs,
                           page=page,
                           has_more=has_more,
                           search_query=search_query,
                           keywords=keywords,
                           total_count=total_count)


@app.route('/discussion', methods=['GET', 'POST'])
def discussion():
    """Discussion page with comments."""
    if request.method == 'POST':
        # Handle form submission for creating a new comment
        username = request.form.get('username')
        email = request.form.get('email')
        body = request.form.get('body')
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')

        if not username or not body or not email:
            comments = Comment.query.filter_by(confirmed=True).order_by(
                Comment.created_at.desc()
            ).all()
            is_htmx = request.headers.get('HX-Request') == 'true'
            return render_template('discussion.html', comments=comments,
                                   error="Username, email, and comment are required", is_htmx=is_htmx)

        # Generate a confirmation token
        confirmation_token = generate_confirmation_token()

        # Create a new comment with confirmed=False
        new_comment = Comment(
            username=username, 
            email=email, 
            body=body, 
            ip_address=ip_address, 
            user_agent=user_agent,
            confirmed=False,
            confirmation_token=confirmation_token
        )

        try:
            # Add the comment to the database
            db.session.add(new_comment)
            db.session.commit()

            # Send confirmation email
            send_confirmation_email(email, confirmation_token, 'comment', new_comment.id)

            # After successful comment creation, return the updated page
            comments = Comment.query.filter_by(confirmed=True).order_by(
                Comment.created_at.desc()
            ).all()
            is_htmx = request.headers.get('HX-Request') == 'true'
            return render_template('discussion.html', comments=comments, 
                                   success="Your comment has been submitted. Please check your email to confirm it.", 
                                   is_htmx=is_htmx)
        except Exception as e:
            db.session.rollback()
            comments = Comment.query.filter_by(confirmed=True).order_by(
                Comment.created_at.desc()
            ).all()
            is_htmx = request.headers.get('HX-Request') == 'true'
            return render_template('discussion.html', comments=comments,
                                   error=str(e), is_htmx=is_htmx)

    # Get all confirmed comments ordered by creation date (newest first)
    comments = Comment.query.filter_by(confirmed=True).order_by(
        Comment.created_at.desc()
    ).all()

    # Check if the request wants HTML or JSON
    if request.args.get('format') != 'json':
        # For HTML requests, check if it's an HTMX request
        is_htmx = request.headers.get('HX-Request') == 'true'
        # Return the template with the is_htmx flag
        return render_template('discussion.html', comments=comments, is_htmx=is_htmx)
    else:
        # Return JSON for API clients
        result = [{"id": comment.id, "username": comment.username, "body": comment.body,
                   "created_at": comment.created_at.isoformat()} for comment in comments]
        return jsonify(result)




@app.route('/comment/<int:comment_id>/answer', methods=['POST'])
def add_answer(comment_id):
    """Add an answer to a comment."""
    comment = Comment.query.get_or_404(comment_id)

    # Get form data
    username = request.form.get('username')
    email = request.form.get('email')
    body = request.form.get('body')
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')

    if not username or not body or not email:
        return f"Error: Username, email, and answer are required", 400

    # Generate a confirmation token
    confirmation_token = generate_confirmation_token()

    # Create new answer with confirmed=False
    new_answer = Answer(
        username=username, 
        email=email, 
        body=body, 
        ip_address=ip_address, 
        user_agent=user_agent, 
        comment_id=comment_id,
        confirmed=False,
        confirmation_token=confirmation_token
    )

    try:
        db.session.add(new_answer)
        db.session.commit()

        # Send confirmation email
        send_confirmation_email(email, confirmation_token, 'answer', new_answer.id)
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}", 500

    # Return the updated comment HTML with success message
    return render_template('comment_partial.html', comment=comment, 
                          answer_success="Your answer has been submitted. Please check your email to confirm it.")


def get_mistral_answer(chat_messages: list[dict], prompt: str):
    """
    Helper function to fetch Mistral answer data.
    """
    # api_key = os.environ["MISTRAL_API_KEY"]
    api_key = ""
    model = "mistral-large-latest"

    client = Mistral(api_key=api_key)

    messages = []
    for cm in chat_messages:
        messages.append({"role": "user", "content": cm["user"]})
        messages.append({"role": "assistant", "content": cm["server"]})
    messages.append({"role": "user", "content": prompt})

    chat_response = client.chat.complete(
        model=model,
        messages=messages
    ).choices[0].message.content
    return chat_response


@app.route('/download')
def download():
    """
    Download page with buttons to download anonymized contributions in CSV and JSON formats.
    """
    return render_template('download.html')


@app.route('/download-file/<file_name>')
def download_file(file_name):
    """
    Route to download any file from the resources directory.

    Args:
        file_name (str): The name of the file within the resources directory

    Returns:
        Response: The file download response
    """
    # List files in resources directory
    resources_path = Path(__file__).resolve().parent.parent / "resources"
    available_files = {fp.name: fp for fp in resources_path.rglob('*')}

    if file_name not in available_files:
        return "Invalid file name", 400

    # Get the requester's IP address
    ip_address = request.remote_addr
    # Get the user agent
    user_agent = request.headers.get('User-Agent', '')

    # Log the download in the database
    download_log = DownloadLog(
        file_name=file_name,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Save the log to the database
    try:
        db.session.add(download_log)
        db.session.commit()
    except Exception as e:
        # Log the error but continue with the request
        print(f"Error logging download: {str(e)}")
        db.session.rollback()

    # Send the file to the client
    return send_from_directory(
        available_files[file_name].parent.resolve(),
        file_name,
        as_attachment=True,
        download_name=file_name
    )


@app.route('/analyse', methods=['GET', 'POST'])
def analyse():
    """
    Analyse page with chat functionality.
    - GET: Initial page load with empty chat
    - POST: Process user prompt and return response
    """
    if request.method == 'POST':
        # Get the user prompt from the form
        prompt = request.form.get('prompt', '')

        if not prompt:
            return "Error: Prompt cannot be empty", 400

        # Get the requester's IP address
        ip_address = request.remote_addr
        # Get the user agent
        user_agent = request.headers.get('User-Agent', '')

        # Get the previous messages from the form (if any)
        previous_messages = json.loads(request.form.get('previous_messages', ''))

        # Create the server response
        server_response = get_mistral_answer(previous_messages, prompt)

        # Log the chat in the database using the new AnalyseChat model
        chat_log = AnalyseChat(
            user_message=prompt,
            server_response=server_response,
            ip_address=ip_address,
            user_agent=user_agent
        )

        try:
            db.session.add(chat_log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"Error logging chat: {str(e)}", 500

        # Return the message exchange HTML
        return render_template('analyse_message.html',
                               user_message=prompt,
                               server_message=server_response)

    # For GET requests, render the initial template
    return render_template('analyse.html')


@app.route('/a-propos')
def a_propos():
    """
    A propos page with information about the author and the project.
    """
    return render_template('a_propos.html')


@app.route('/confirm/<content_type>/<int:content_id>/<token>')
def confirm_content(content_type, content_id, token):
    """
    Confirm a comment or answer by validating the token.

    Args:
        content_type (str): Either 'comment' or 'answer'
        content_id (int): The ID of the comment or answer
        token (str): The confirmation token
    """
    if content_type not in ['comment', 'answer']:
        return "Invalid content type", 400

    # Get the content based on type
    if content_type == 'comment':
        content = Comment.query.get_or_404(content_id)
    else:  # content_type == 'answer'
        content = Answer.query.get_or_404(content_id)

    # Validate the token
    if content.confirmation_token != token:
        return "Invalid or expired confirmation token", 400

    # Mark the content as confirmed
    content.confirmed = True

    try:
        db.session.commit()
        return render_template('confirmation_success.html', content_type=content_type)
    except Exception as e:
        db.session.rollback()
        return f"Error confirming {content_type}: {str(e)}", 500
