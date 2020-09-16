conda activate sqlenv
eralchemy -i postgresql://postgres:password@localhost:5433/opencelldb-test -o schema-diagram.png
conda deactivate
