from flask import Flask, render_template, redirect, url_for, request, flash, session, send_file, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import login_manager
from models import User, Time, db
from forms import LoginForm, AddUserForm
from config import Config
from datetime import datetime, timedelta
import os
from scramble import generate_scramble

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cube_timer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_TYPE'] = 'filesystem'

db.init_app(app)

with app.app_context():
    db.create_all()

login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=7)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('timer'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('timer'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=True)
            session['user_id'] = user.id
            session['last_activity'] = datetime.utcnow().timestamp()
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('timer'))
        flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    flash('Successfully logged out', 'success')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    times = Time.query.filter_by(user_id=current_user.id).order_by(Time.time_seconds).all()
    best_time = min([time.time_seconds for time in times]) if times else None
    best_time_date = next((time.date for time in times if time.time_seconds == best_time), None)
    total_solves = len(times)
    average_time = sum([time.time_seconds for time in times]) / total_solves if times else None
    
    return render_template('profile.html', 
                         times=times, 
                         best_time=best_time,
                         best_time_date=best_time_date,
                         total_solves=total_solves,
                         average_time=average_time)


@app.route('/timer')
@login_required
def timer():
    times = Time.query.filter_by(user_id=current_user.id).order_by(Time.date.desc()).all()
    return render_template('timer.html', times=times)

@app.route('/get_scramble')
def get_scramble():
    cube_type = request.args.get('type', '3x3')
    scramble = generate_scramble(cube_type)
    return jsonify({'scramble': scramble})

@app.route('/save_time', methods=['POST'])
@login_required
def save_time():
    data = request.json
    print(f"Saving time: {data}")  # Debug print to verify data
    
    if not all(key in data for key in ['time', 'cubeType', 'scramble']):
        return jsonify({'status': 'error', 'message': 'Missing required data'}), 400
        
    new_time = Time(
        time_seconds=float(data['time']),
        cube_type=data['cubeType'],
        scramble=data['scramble'],
        user_id=current_user.id
    )
    db.session.add(new_time)
    db.session.commit()
    
    print(f"Time saved successfully: ID={new_time.id}")  # Confirm save
    return jsonify({'status': 'success'})



@app.route('/download_times/<int:user_id>')
@login_required
def download_times(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        return redirect(url_for('timer'))
    
    user = User.query.get_or_404(user_id)
    times = Time.query.filter_by(user_id=user_id).order_by(Time.date.desc()).all()
    
    times_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'times')
    if not os.path.exists(times_dir):
        os.makedirs(times_dir)
    
    filename = os.path.join(times_dir, f'{user.username}_times.txt')
    with open(filename, 'w') as f:
        f.write(f"Times for {user.username}\n")
        f.write("=" * 30 + "\n\n")
        for time in times:
            f.write(f"Time: {time.time_seconds:.2f}s - Cube: {time.cube_type} - Date: {time.date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Scramble: {time.scramble}\n\n")
    
    return send_file(filename, as_attachment=True, download_name=f'{user.username}_times.txt')

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('timer'))
    
    form = AddUserForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            username=form.username.data,
            password=hashed_password,
            is_admin=form.is_admin.data
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User added successfully')
        return redirect(url_for('admin'))

    users = User.query.all()
    times = Time.query.order_by(Time.date.desc()).all()
    return render_template('admin.html', users=users, times=times, form=form)

@app.route('/admin/user_stats/<int:user_id>')
@login_required
def user_stats(user_id):
    if not current_user.is_admin:
        return redirect(url_for('timer'))
    
    user = User.query.get_or_404(user_id)
    times = Time.query.filter_by(user_id=user_id).order_by(Time.date.desc()).all()
    
    stats = {
        'total_solves': len(times),
        'best_time': min([time.time_seconds for time in times]) if times else 0,
        'average_time': sum([time.time_seconds for time in times]) / len(times) if times else 0,
        'times_by_cube': {}
    }
    
    # Group times by cube type
    for time in times:
        if time.cube_type not in stats['times_by_cube']:
            stats['times_by_cube'][time.cube_type] = []
        stats['times_by_cube'][time.cube_type].append(time)
    
    return render_template('user_stats.html', user=user, stats=stats, times=times)



@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('timer'))
    
    user = User.query.get_or_404(user_id)
    form = AddUserForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.is_admin = form.is_admin.data
        db.session.commit()
        flash('User updated successfully')
        return redirect(url_for('admin'))
    
    return render_template('edit_user.html', form=form, user=user)

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('timer'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot delete your own account')
        return redirect(url_for('admin'))
    
    filename = os.path.join('times', f'{user.username}_times.txt')
    if os.path.exists(filename):
        os.remove(filename)
    
    Time.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    from app import app, db

    with app.app_context():
        db.create_all()
        
        # Create admin user only if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                password=generate_password_hash('admin'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()

    print(' * Server running at http://localhost:5000')
    print(' * For local network access use: http://<your-local-ip>:5000')
    app.run(host='0.0.0.0', port=5000, debug=True)




