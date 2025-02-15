import os
from sqlalchemy import func
from flask import Flask, render_template, send_from_directory
from config import Config
from models import db, Media
from routes import api  # Import the Blueprint
from datetime import datetime, timedelta
from sqlalchemy import desc, extract, func

app = Flask(__name__)
app.config.from_object(Config)


UPLOAD_FOLDER = 'media'

# Ensure media folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Database
db.init_app(app)

# Register Blueprint
app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def dashboard():
    # Get the current time
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Fetch the last 24 hours efficiency data
    hourly_data = {f"{hour}:00": 0 for hour in range(24)}  # Initialize with 0 for all hours

    efficiency_results = (
        Media.query.with_entities(
            extract('hour', Media.created_at).label("hour"),
            func.sum(Media.number_of_input).label("total_input")
        )
        .filter(Media.created_at >= start_of_day)
        .group_by("hour")
        .all()
    )

    # Populate the hourly_data dictionary with actual values
    for result in efficiency_results:
        hour_label = f"{int(result.hour)}:00"
        hourly_data[hour_label] = result.total_input if result.total_input else 0

    # Fetch last 20 images ordered by created_at descending
    last_20_images = (
        Media.query.order_by(desc(Media.created_at))
        .limit(20)
        .with_entities(Media.image_src)
        .all()
    )

    # Convert to a list of image file names
    last_20_images = [img.image_src for img in last_20_images if img.image_src]

    return render_template("index.html", last_20_images=last_20_images, hourly_data=hourly_data)

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory('./', filename)

if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True, host="0.0.0.0", port=3000)
