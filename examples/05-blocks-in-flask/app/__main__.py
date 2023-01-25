from flask import Flask, render_template, request
from . import logic

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def main():
  if request.method == 'GET':
    return render_template('form.html')
  else:
    solution = logic.get_solution(request.form)
    return render_template('form.html', solution=solution)

if __name__ == '__main__':
  app.run()

