from flask import Flask, render_template, request
from . import logic

app = Flask(__name__)

@app.route('/')
def display():
  return render_template('form.html')

@app.route('/', methods=['POST'])
def respond():
  solution = logic.get_solution(request.form)
  return render_template('form.html', solution=solution)

if __name__ == '__main__':
  app.run()

