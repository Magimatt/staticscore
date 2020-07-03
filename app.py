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

class movie_scores(db.Model):
  date_created = db.Column(db.DateTime, default=datetime.utcnow, primary_key=True)
  tmdb_id = db.Column(db.String(200), nullable=False)
  posiscore = db.Column(db.Integer, nullable=False)
  negascore = db.Column(db.Integer, nullable=False)

  def __repr__(self):
    return '<score %r>' % self.tmdb_id

  def average_posi(self, posiscore):
    #TODO: Return an average posiscore from the "Scores" table
    return
  
  def average_nega(self, negascore):
    #TODO: Return an average negascore from the "Scores" table
    return


class movie_info(db.Model):
  tmdb_id = db.Column(db.Integer, default=0, primary_key=True)
  movie_name = db.Column(db.String(200), nullable=False)
  ave_posiscore = db.Column(db.Float, nullable=False)
  ave_negascore = db.Column(db.Float, nullable=False)
  ave_combscore = db.Column(db.Float, nullable=False)

  def __repr__(self):
    return '<movie %r>' % self.tmdb_id


app.secret_key = "It's a secret to everybody"
TMDB_KEY = os.getenv('TMDB_KEY')
tmdb.API_KEY = TMDB_KEY

search_movies = tmdb.Search()

@app.route("/", methods=['GET'])
def index():
  return render_template("index.html")

@app.route("/results", methods=['POST', 'GET'])
def results():
  if request.method == 'POST':
    posiscore_vote = request.form['posiscore_vote']
    negascore_vote = request.form['negascore_vote']
    new_score = movie_scores(tmdb_id="", posiscore=posiscore_vote, negascore=negascore_vote)

  else:
    search_text = request.args.get('search', '')
    response = search_movies.movie(query=search_text)

    return render_template("results.html", results=response['results'], search_text=search_text)

if __name__ == '__main__':
  app.run(debug=True)