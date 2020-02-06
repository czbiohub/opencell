conda activate sqlenv
eralchemy -i postgresql://postgres:password@localhost:5434/opencelldb_dev -o schema-diagram.png
conda deactivate
