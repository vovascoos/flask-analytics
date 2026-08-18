from flask import Flask, render_template, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///analytics.db'
db = SQLAlchemy(app)


class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(200))
    visitor_id = db.Column(db.String(64))
    ip = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/track.js')
def track_js():
    return '''document.addEventListener('DOMContentLoaded', function() {
        var data = {
            page: window.location.pathname,
            visitor: localStorage.getItem('visitor_id') || (function() {
                var id = 'v_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
                localStorage.setItem('visitor_id', id);
                return id;
            })()
        };
        fetch('/track', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    });''', 200, {'Content-Type': 'application/javascript'}


@app.route('/track', methods=['POST'])
def track():
    data = request.get_json()
    visit = Visit(
        page=data.get('page', '/'),
        visitor_id=data.get('visitor', 'unknown'),
        ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(visit)
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/stats')
def stats():
    total_visits = Visit.query.count()
    unique_visitors = db.session.query(Visit.visitor_id).distinct().count()
    pages = db.session.query(Visit.page, db.func.count(Visit.id)).group_by(Visit.page).all()
    visits_by_day = db.session.query(
        db.func.date(Visit.timestamp),
        db.func.count(Visit.id)
    ).group_by(db.func.date(Visit.timestamp)).order_by(db.func.date(Visit.timestamp).desc()).limit(7).all()

    return render_template('stats.html',
                           total=total_visits,
                           unique=unique_visitors,
                           pages=pages,
                           daily=visits_by_day
                           )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)