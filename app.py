#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\
# Import Statements
#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\

import os
import uuid

import tmdbsimple as tmdb
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import (
    Flask,
    flash, 
    render_template, 
    redirect,
    request,
    url_for,
    escape,
    make_response
)

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moviescores.db'
db = SQLAlchemy(app)

#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\
# SQLalchemy Database Classes
#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\
class MovieInfo(db.Model):
  tmdb_id = db.Column(db.String, primary_key=True)
  movie_name = db.Column(db.String(200), nullable=False) # fun trivia: current longest movie title is 196 characters long.
  ave_posiscore = db.Column(db.Float, default=0)
  ave_negascore = db.Column(db.Float, default=0)
  ave_combscore = db.Column(db.Float, default=0)

  def __repr__(self):
    return '<Movie %r>' % self.movie_name

class MovieScores(db.Model):
  date_created = db.Column(db.DateTime, default=datetime.utcnow, primary_key=True)
  user_id = db.Column(db.String(36), nullable=False)
  tmdb_id = db.Column(db.String(200), nullable=False)
  posiscore = db.Column(db.Integer, nullable=False)
  negascore = db.Column(db.Integer, nullable=False)

  def __repr__(self):
    return '<Score %r>' % self.tmdb_id


#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\
# Flask Minutia
#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\

app.secret_key = "It's a secret to everybody"
TMDB_KEY = os.getenv('TMDB_KEY')
tmdb.API_KEY = TMDB_KEY

search_movies = tmdb.Search()

def average_posi(_tmdb_id):
  return db.session.execute("SELECT AVG(posiscore) FROM movie_scores WHERE tmdb_id=" + _tmdb_id).first()['AVG(posiscore)']

def average_nega(_tmdb_id):
  return db.session.execute("SELECT AVG(negascore) FROM movie_scores WHERE tmdb_id=" + _tmdb_id).first()['AVG(negascore)']

def average_table_scores(_tmdb_id):
  posi = db.session.execute("SELECT AVG(posiscore) FROM movie_scores WHERE tmdb_id=" + _tmdb_id).first()['AVG(posiscore)']
  nega = db.session.execute("SELECT AVG(negascore) FROM movie_scores WHERE tmdb_id=" + _tmdb_id).first()['AVG(negascore)']
  
  return posi, nega, ((posi + nega) / 2) # TODO: weight the combined score
  
def validate_input(text):
  try:
    int(text)
    if (int(text) <= 10) and (int(text) >= 0):
      return True
    else:
      return False
  except ValueError:
    return False
  
def cookie_check(): #TODO: fix cookies
  if not "user_id" in request.cookies:
    return False
  else:
    return True

#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\
# Flask App Routes
#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\

@app.route("/", methods=['GET'])
def index():
  has_cookie = cookie_check()
  
  movies = MovieInfo.query.all()
  movies_order_posi = sorted(movies, key=lambda m: m.ave_posiscore, reverse=True)[:10]
  movies_order_nega = sorted(movies, key=lambda m: m.ave_negascore, reverse=True)[:10]
  movies_order_comb = sorted(movies, key=lambda m: m.ave_combscore, reverse=True)[:10]
  
  # Set cookies if has_cookie is False
  if has_cookie:
    return render_template("index.html", 
                           top_posi=movies_order_posi, 
                           top_nega=movies_order_nega, 
                           top_comb=movies_order_comb)
  else:
    resp = make_response(render_template("index.html", 
                                         top_posi=movies_order_posi, 
                                         top_nega=movies_order_nega, 
                                         top_comb=movies_order_comb))
    resp.set_cookie("user_id", str(uuid.uuid4()))
    return resp

@app.route("/results", methods=['POST', 'GET'])
def results():
  has_cookie = cookie_check()
  
  search_text = str(escape(request.args.get('search', '')))
  response = search_movies.movie(query=search_text)
  results = response['results']
    
  ids = [movie['id'] for movie in results]
  user_votes = MovieScores.query.filter(MovieScores.user_id == request.cookies.get('user_id'),
                                        MovieScores.tmdb_id in ids).all()
  
  new_results = []
  for movie in results:
    _votes = [vote for vote in user_votes if vote.tmdb_id == movie["id"]]
    if len(_votes) > 0:
      user_vote = _votes[0]
    else:
      user_vote = None

    movie['user_vote'] = user_vote
    new_results.append(movie)
    vote_value = ""    # This is needed in the template to determine if the user has voted on a movie before.
  
  if has_cookie:
    return render_template("results.html", results=new_results, 
                           search_text=search_text, 
                           user_votes=user_votes, 
                           vote_value=vote_value)
  else:
    resp = make_response(render_template("results.html", results=new_results, 
                                         search_text=search_text, 
                                         user_votes=user_votes, 
                                         vote_value=vote_value))
    resp.set_cookie("user_id", str(uuid.uuid4()))
    return resp

@app.route("/vote", methods=['POST'])
def vote():
  if not cookie_check():
    flash("Hey A-hole! Stop trying to game the system... or maybe you're just an innocent bystander just trying to avoid cookies.")
  else:
    pass
  
  if (not(validate_input(request.form['ps-vote'])) or not(validate_input(request.form['ns-vote']))):
    flash("An error occured. Please input only numbers 1 through 10 into the poll boxes and try again.")
    
  else:
    posi_score = request.form['ps-vote']
    nega_score = request.form['ns-vote']
    movie_title = request.form['movie-title']
    movie_id = request.form['movie-id']
    cookie = request.cookies.get('user_id')
    new_score = MovieScores(user_id=cookie, 
                            tmdb_id=movie_id, 
                            posiscore=posi_score, 
                            negascore=nega_score)

    db.session.add(new_score)
    db.session.commit()
    score_triuple = average_table_scores(movie_id)
    existing_movie = MovieInfo.query.filter_by(tmdb_id=movie_id).first()

    try:
      if existing_movie == None:
        new_movie = MovieInfo(tmdb_id=movie_id,
                              movie_name=movie_title,
                              ave_posiscore=score_triuple[0],
                              ave_negascore=score_triuple[1],
                              ave_combscore=score_triuple[2])
        db.session.add(new_movie)

      else:
        existing_movie.ave_posiscore = score_triuple[0]
        existing_movie.ave_negascore = score_triuple[1]
        existing_movie.ave_combscore = score_triuple[2]

      db.session.commit()    
      flash("You're scores have been recorded.")
    except:
      flash("An error occured when submitting your vote. Please try again later.")

  return redirect('/')

if __name__ == '__main__':
  app.run(debug=True)