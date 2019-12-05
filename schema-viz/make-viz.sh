psql -f schema.sql -v dbname="pipeline_test"
conda activate sqlenv
eralchemy -i 'postgresql+psycopg2://keith.cheveralls@localhost:5432/pipeline_test' -o schema-viz.png
conda deactivate
