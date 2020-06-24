# on puhti
source /projappl/project_2002820/venv/annotool/bin/activate

# this one required for epsilon
#export PYTHONPATH=/home/lhchan/para-anno/

export FLASK_ENV=development
export FLASK_APP=paraanno.app
export PARAANN_DATA=/scratch/project_2002820/lihsin/para-data

if [ "$#" -eq 1 ]; then
    PORT=$1
    flask run --port $PORT
else
    flask run
fi

export PARAANN_DATA=$HOME/Turku-paraphrase-corpus/para-subtitles
flask run

