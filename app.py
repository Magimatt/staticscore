#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\
# Import Statements
#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\

import os

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


#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\
# Flask App Routes
#/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\

@app.route("/", methods=['GET'])
def index():
  movies = MovieInfo.query.all()
  movies_order_posi = sorted(movies, key=lambda m: m.ave_posiscore, reverse=True)[:10]
  movies_order_nega = sorted(movies, key=lambda m: m.ave_negascore, reverse=True)[:10]
  movies_order_comb = sorted(movies, key=lambda m: m.ave_combscore, reverse=True)[:10]
  
  return render_template("index.html", top_posi=movies_order_posi, top_nega=movies_order_nega, top_comb=movies_order_comb)

@app.route("/results", methods=['POST', 'GET'])
def results():
  search_text = request.args.get('search', '')
  response = search_movies.movie(query=search_text)

  return render_template("results.html", results=response['results'], search_text=search_text)

@app.route("/vote", methods=['POST'])
def vote():
  movie_title = request.form['movie-title']
  movie_id = request.form['movie-id']
  posi_score = request.form['ps-vote']
  nega_score = request.form['ns-vote']
  new_score = MovieScores(tmdb_id=movie_id, posiscore=posi_score, negascore=nega_score)

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
    flash("An error occured when submitting. Please try again later.")
    
  return redirect('/')

if __name__ == '__main__':
  app.run(debug=True)