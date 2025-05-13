import json
import re
from pathlib import Path

from flask import render_template, request, jsonify, redirect, send_from_directory
from markupsafe import Markup
from mistralai import Mistral
from sqlalchemy import or_

from app import app, db
from app.models import Contribution, Comment, Answer, SearchLog, AnalyseChat, DownloadLog
from app.utils import generate_captcha, validate_captcha


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
    is_htmx = request.headers.get('HX-Request') == 'true'

    def get_db_comments():
        return Comment.query.order_by(Comment.created_at.desc()).all()

    def generate_captcha_for_comment_answers():
        # Generate captchas for each answer form
        answer_captcha_texts = {}
        answer_captcha_images = {}
        for comment in get_db_comments():  # Get all comments ordered by creation date (newest first)
            answer_captcha_text, answer_captcha_image = generate_captcha()
            answer_captcha_texts[comment.id] = answer_captcha_text
            answer_captcha_images[comment.id] = answer_captcha_image
        return answer_captcha_texts, answer_captcha_images

    if request.method == 'POST':
        # Handle form submission for creating a new comment
        username = request.form.get('username')
        body = request.form.get('body')
        captcha_input = request.form.get('captcha')
        captcha_text = request.form.get('captcha_text')
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')

        # Generate a new captcha for the form
        new_captcha_text, new_captcha_image = generate_captcha()
        answer_captcha_texts, answer_captcha_images = generate_captcha_for_comment_answers()

        if not username or not body:
            return render_template('discussion.html', comments=get_db_comments(),
                                   error="Username and comment are required",
                                   captcha_text=new_captcha_text,
                                   captcha_image=new_captcha_image,
                                   answer_captcha_texts=answer_captcha_texts,
                                   answer_captcha_images=answer_captcha_images,
                                   is_htmx=is_htmx)

        # Validate the captcha
        if not validate_captcha(captcha_input, captcha_text):
            return render_template('discussion.html', comments=get_db_comments(),
                                   error="Invalid captcha. Please try again.",
                                   captcha_text=new_captcha_text,
                                   captcha_image=new_captcha_image,
                                   answer_captcha_texts=answer_captcha_texts,
                                   answer_captcha_images=answer_captcha_images,
                                   is_htmx=is_htmx)

        # Create a new comment
        new_comment = Comment(
            username=username,
            body=body,
            ip_address=ip_address,
            user_agent=user_agent
        )

        try:
            # Add the comment to the database
            db.session.add(new_comment)
            db.session.commit()

            # After successful comment creation, return the updated page
            answer_captcha_texts, answer_captcha_images = generate_captcha_for_comment_answers()
            return render_template('discussion.html', comments=get_db_comments(),
                                   success="Your comment has been submitted successfully.",
                                   captcha_text=new_captcha_text,
                                   captcha_image=new_captcha_image,
                                   answer_captcha_texts=answer_captcha_texts,
                                   answer_captcha_images=answer_captcha_images,
                                   is_htmx=is_htmx)
        except Exception as e:
            db.session.rollback()
            return render_template('discussion.html', comments=get_db_comments(),
                                   error=str(e),
                                   captcha_text=new_captcha_text,
                                   captcha_image=new_captcha_image,
                                   answer_captcha_texts=answer_captcha_texts,
                                   answer_captcha_images=answer_captcha_images,
                                   is_htmx=is_htmx)


    # Check if the request wants HTML or JSON
    if request.args.get('format') != 'json':
        # Generate captcha for the comment form and for each answers form
        captcha_text, captcha_image = generate_captcha()
        answer_captcha_texts, answer_captcha_images = generate_captcha_for_comment_answers()
        return render_template('discussion.html',
                               comments=get_db_comments(),
                               captcha_text=captcha_text,
                               captcha_image=captcha_image,
                               answer_captcha_texts=answer_captcha_texts,
                               answer_captcha_images=answer_captcha_images,
                               is_htmx=is_htmx)
    else:
        # Return JSON for API clients
        result = [{"id": comment.id, "username": comment.username, "body": comment.body,
                   "created_at": comment.created_at.isoformat()} for comment in get_db_comments()]
        return jsonify(result)


@app.route('/comment/<int:comment_id>/answer', methods=['POST'])
def add_answer(comment_id):
    """Add an answer to a comment."""
    comment = Comment.query.get_or_404(comment_id)

    # Get form data
    username = request.form.get('username')
    body = request.form.get('body')
    captcha_input = request.form.get('captcha')
    captcha_text = request.form.get('captcha_text')
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')

    # Generate a new captcha for the answer form
    new_captcha_text, new_captcha_image = generate_captcha()

    # Generate captchas for all answer forms
    answer_captcha_texts = {comment.id: new_captcha_text}
    answer_captcha_images = {comment.id: new_captcha_image}

    if not username or not body:
        return render_template('comment_partial.html', comment=comment,
                               error="Username and answer are required",
                               answer_captcha_texts=answer_captcha_texts,
                               answer_captcha_images=answer_captcha_images)

    # Validate the captcha
    if not validate_captcha(captcha_input, captcha_text):
        return render_template('comment_partial.html', comment=comment,
                               error="Invalid captcha. Please try again.",
                               answer_captcha_texts=answer_captcha_texts,
                               answer_captcha_images=answer_captcha_images)

    # Create new answer
    new_answer = Answer(
        username=username,
        body=body,
        ip_address=ip_address,
        user_agent=user_agent,
        comment_id=comment_id
    )

    try:
        db.session.add(new_answer)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template('comment_partial.html', comment=comment,
                               error=f"Error: {str(e)}",
                               answer_captcha_texts=answer_captcha_texts,
                               answer_captcha_images=answer_captcha_images)

    # Return the updated comment HTML with success message
    return render_template('comment_partial.html', comment=comment,
                           answer_success="Your answer has been submitted successfully.",
                           answer_captcha_texts=answer_captcha_texts,
                           answer_captcha_images=answer_captcha_images)


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
